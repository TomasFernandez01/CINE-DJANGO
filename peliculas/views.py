from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Pelicula
from django.core.files.base import ContentFile
import requests
from django.http import JsonResponse  # nuevo: para el endpoint del buscador en vivo
from django.urls import reverse  # nuevo: para armar la url de cada resultado del buscador en vivo

# Importar cliente TMDB
try:
    from utils.tmdb_api import TMDBClient, buscar_pelicula_tmdb, importar_pelicula_tmdb
    TMDB_DISPONIBLE = True
except ImportError:
    TMDB_DISPONIBLE = False


# ============================================
# VISTAS EXISTENTES (mantener como están)
# ============================================

def inicio(request):
    # se envia la cartelera real al home; el carrusel de fechas se movio a lista_peliculas
    # (pertenece a la app peliculas / cartelera, no al home) por pedido del cliente
    peliculas_cartelera = Pelicula.objects.filter(en_cartelera=True).order_by('-fecha_estreno')[:8]

    # nuevo: posters disponibles para el hero rotativo (solo las que tienen poster cargado)
    posters_hero = [p for p in peliculas_cartelera if p.poster]

    return render(request, 'inicio.html', {
        'peliculas_cartelera': peliculas_cartelera,
        'posters_hero': posters_hero,
    })

def lista_peliculas(request):
    # ... código existente ...
    peliculas = Pelicula.objects.filter(en_cartelera=True)
    
    busqueda = request.GET.get('buscar', '')
    if busqueda:
        query = Q(titulo__icontains=busqueda)
        if hasattr(Pelicula, 'director') and Pelicula._meta.get_field('director'):
            query |= Q(director__icontains=busqueda)
        if hasattr(Pelicula, 'actores') and Pelicula._meta.get_field('actores'):
            query |= Q(actores__icontains=busqueda)
        peliculas = peliculas.filter(query)
    
    genero = request.GET.get('genero', '')
    if genero:
        peliculas = peliculas.filter(genero=genero)
    
    clasificacion = request.GET.get('clasificacion', '')
    if clasificacion:
        peliculas = peliculas.filter(clasificacion=clasificacion)
    
    orden = request.GET.get('orden', 'titulo')
    if orden == 'titulo':
        peliculas = peliculas.order_by('titulo')
    elif orden == 'año':
        if hasattr(Pelicula, 'año'):
            peliculas = peliculas.order_by('-año', 'titulo')
        else:
            peliculas = peliculas.order_by('titulo')
    elif orden == 'genero':
        peliculas = peliculas.order_by('genero', 'titulo')
    
    generos_disponibles = Pelicula.GENERO_CHOICES
    clasificaciones_disponibles = Pelicula.CLASIFICACION_CHOICES
    
    hay_filtros_activos = bool(busqueda or genero or clasificacion)

    # nuevo: separar "en cartelera" (ya estrenada) de "proximos estrenos" (fecha_estreno a futuro),
    # usando el campo Pelicula.fecha_estreno que ya existia. Solo se separa cuando no hay
    # filtros activos, porque con busqueda/filtro se muestra un listado plano de resultados.
    hoy = timezone.now().date()
    peliculas_en_cartelera = None
    peliculas_proximos_estrenos = None
    if not hay_filtros_activos:
        peliculas_en_cartelera = peliculas.filter(
            Q(fecha_estreno__isnull=True) | Q(fecha_estreno__lte=hoy)
        )
        peliculas_proximos_estrenos = peliculas.filter(fecha_estreno__gt=hoy)

    # nuevo: carrusel de fechas (movido desde inicio.html), apunta a salas:lista_funciones?fecha=YYYY-MM-DD
    proximas_fechas = []
    for i in range(8):
        dia = hoy + timezone.timedelta(days=i)
        proximas_fechas.append({
            'valor': dia.strftime('%Y-%m-%d'),
            'dia_semana': 'Hoy' if i == 0 else dia.strftime('%a').capitalize(),
            'dia_mes': dia.strftime('%d/%m'),
        })

    contexto = {
        'peliculas': peliculas,
        'peliculas_en_cartelera': peliculas_en_cartelera,
        'peliculas_proximos_estrenos': peliculas_proximos_estrenos,
        'hay_filtros_activos': hay_filtros_activos,
        'busqueda': busqueda,
        'genero_seleccionado': genero,
        'clasificacion_seleccionada': clasificacion,
        'orden_seleccionado': orden,
        'generos_disponibles': generos_disponibles,
        'clasificaciones_disponibles': clasificaciones_disponibles,
        'total_resultados': peliculas.count(),
        'proximas_fechas': proximas_fechas,
    }
    return render(request, 'peliculas/lista_pelis.html', contexto)


def buscar_vivo(request):
    """nuevo: endpoint JSON para el buscador en vivo (autocompletado) de la cartelera.
    Se consulta con fetch() desde JS a medida que el usuario escribe/borra."""
    query = request.GET.get('q', '').strip()
    resultados = []
    if len(query) >= 2:
        peliculas = Pelicula.objects.filter(
            en_cartelera=True, titulo__icontains=query
        ).order_by('titulo')[:8]
        for p in peliculas:
            resultados.append({
                'id': p.id,
                'titulo': p.titulo,
                'poster_url': p.poster.url if p.poster else None,
                'genero': p.get_genero_display() if p.genero else '',
                'url': reverse('peliculas:detalle_pelicula', args=[p.id]),
            })
    return JsonResponse({'resultados': resultados})

def detalle_pelicula(request, pelicula_id):
    pelicula = get_object_or_404(Pelicula, id=pelicula_id)
    ahora = timezone.now()
    funciones = pelicula.funciones.filter(
        disponible=True,
        fecha_hora__gt=ahora
    ).select_related('sala').order_by('fecha_hora')
    
    contexto = {
        'pelicula': pelicula,
        'funciones': funciones,
    }
    return render(request, 'peliculas/detalle_pelicula.html', contexto)

# ============================================
# UTILIDAD PARA DESCARGAR POSTERS
# ============================================

############################################################# V 1
def descargar_poster(poster_url, titulo):
    """
    Descarga el poster desde TMDB y retorna un ContentFile.
    """
    try:
        response = requests.get(poster_url, timeout=10)
        response.raise_for_status()
        
        # Crear nombre de archivo seguro
        nombre_archivo = f"{titulo.lower().replace(' ', '_')[:50]}.jpg"
        
        # Retornar ContentFile que Django puede guardar
        return ContentFile(response.content, name=nombre_archivo)
    except Exception as e:
        print(f"Error descargando poster: {e}")
        return None
############################################################# V 2

# ============================================
# NUEVAS VISTAS PARA TMDB
# ============================================

@staff_member_required  # Solo staff puede acceder
def buscar_tmdb(request):
    """
    Vista para buscar películas en TMDB y agregarlas a la base de datos.
    Accesible solo para staff/admin.
    """
    if not TMDB_DISPONIBLE:
        messages.error(request, 'La integración con TMDB no está configurada.')
        return redirect('admin:index')
    
    resultados = []
    query = ''
    
    if request.method == 'GET' and 'q' in request.GET:
        query = request.GET.get('q', '').strip()
        
        if query:
            response = buscar_pelicula_tmdb(query)
            
            if response['success']:
                resultados = response['results']
                if not resultados:
                    messages.info(request, f'No se encontraron resultados para "{query}"')
            else:
                messages.error(request, f'Error al buscar: {response.get("error")}')
    
    contexto = {
        'query': query,
        'resultados': resultados,
        'tmdb_disponible': TMDB_DISPONIBLE,
    }
    return render(request, 'peliculas/buscar_tmdb.html', contexto)


@staff_member_required
def importar_tmdb(request, tmdb_id):
    """
    Importa una película desde TMDB y la guarda en la base de datos.

    NUEVO:
    Importa una película desde TMDB con POSTER incluido.
    CORREGIDO: Guarda primero la película, DESPUÉS el poster.

    """
    if not TMDB_DISPONIBLE:
        messages.error(request, 'La integración con TMDB no está configurada.')
        return redirect('admin:index')
    
    # Obtener detalles de TMDB
    response = importar_pelicula_tmdb(tmdb_id)
    
    if not response['success']:
        messages.error(request, f'Error al obtener detalles: {response.get("error")}')
        return redirect('peliculas:buscar_tmdb')
    
    data = response['data']
    
    # Verificar si ya existe
    pelicula_existente = Pelicula.objects.filter(titulo__iexact=data['titulo']).first()
    
    if pelicula_existente:
        messages.warning(request, f'La película "{data["titulo"]}" ya existe en la base de datos.')
        return redirect('admin:peliculas_pelicula_change', pelicula_existente.id)
    
    # ============================================
    # CORRECCIÓN: Crear y guardar SIN poster primero
    # ============================================

    ################################################## V1 : Crear nueva película antes conectado con laárte de POSTER
    # pelicula = Pelicula.objects.create(
    #     titulo=data['titulo'][:50],  # Respetar el límite de caracteres
    #     sinopsis=data.get('sinopsis', ''),
    #     duracion=data.get('duracion'),
    #     genero=data.get('genero'),
    #     clasificacion=data.get('clasificacion', 'ATP'),
    #     director=data.get('director', ''),
    #     actores=data.get('actores', ''),
    #     año=data.get('año'),
    #     en_cartelera=False,  # Por defecto no en cartelera
    # )
    ################################################## V 2
    try:
        pelicula = Pelicula.objects.create(
            titulo=data['titulo'][:50],
            sinopsis=data.get('sinopsis', ''),
            duracion=data.get('duracion'),
            genero=data.get('genero'),
            clasificacion=data.get('clasificacion', 'ATP'),
            director=data.get('director', ''),
            actores=data.get('actores', ''),
            año=data.get('año'),
            en_cartelera=False,
        )
        
        # AHORA sí, descargar y agregar el poster
        poster_url = data.get('poster_url')
        poster_descargado = False
        
        if poster_url:
            try:
                poster_file = descargar_poster(poster_url, data['titulo'])
                if poster_file:
                    # Guardar el poster en la película YA EXISTENTE en la BD
                    pelicula.poster.save(poster_file.name, poster_file, save=True)
                    poster_descargado = True
            except Exception as e:
                print(f"Error descargando poster: {e}")
        
        # Mensaje de éxito
        if poster_descargado:
            messages.success(
                request,
                f'✅ Película "{pelicula.titulo}" importada con poster incluido.'
            )
        else:
            messages.success(
                request,
                f'✅ Película "{pelicula.titulo}" importada (poster no disponible o falló descarga).'
            )
        
        # Redirigir al admin para editar
        return redirect('admin:peliculas_pelicula_change', pelicula.id)
        
    except Exception as e:
        messages.error(request, f'Error al crear la película: {str(e)}')
        return redirect('peliculas:buscar_tmdb')
    ####################################################################### esto era funcional
    # messages.success(
    #     request,
    #     f'✅ Película "{pelicula.titulo}" importada exitosamente. '
    #     f'Ahora podés editarla y subir el poster manualmente.'
    # )
    # # Redirigir al admin para editar
    # return redirect('admin:peliculas_pelicula_change', pelicula.id)
    #######################################################################
    
    # ########################################################## POSTER <--------
    # # NUEVO: Descargar y guardar el poster automáticamente
    poster_url = data.get('poster_url')
    if poster_url:
        try:
            poster_file = descargar_poster(poster_url, data['titulo'])
            if poster_file:
                pelicula.poster.save(poster_file.name, poster_file, save=False)
                messages.success(
                    request,
                    f'✅ Película "{pelicula.titulo}" importada con poster incluido.'
                )
            else:
                messages.success(
                    request,
                    f'✅ Película "{pelicula.titulo}" importada (poster no disponible).'
                )
        except Exception as e:
            messages.warning(
                request,
                f'✅ Película "{pelicula.titulo}" importada pero no se pudo descargar el poster: {str(e)}'
            )
    else:
        messages.success(
            request,
            f'✅ Película "{pelicula.titulo}" importada (sin poster en TMDB).'
        )
    
    # Guardar la película
    pelicula.save()
    
    # Redirigir al admin para editar
    return redirect('admin:peliculas_pelicula_change', pelicula.id)

@staff_member_required
def actualizar_desde_tmdb(request, pelicula_id):
    """
    Actualiza una película existente con datos de TMDB.
    NUEVO:
    Actualiza una película existente con datos de TMDB (incluyendo poster).
    """
    if not TMDB_DISPONIBLE:
        messages.error(request, 'La integración con TMDB no está configurada.')
        return redirect('admin:peliculas_pelicula_change', pelicula_id)
    
    pelicula = get_object_or_404(Pelicula, id=pelicula_id)
    
    if request.method == 'POST':
        tmdb_id = request.POST.get('tmdb_id')
        
        if not tmdb_id:
            messages.error(request, 'Debes proporcionar un ID de TMDB')
            return redirect('admin:peliculas_pelicula_change', pelicula_id)
        
        # Obtener datos de TMDB
        response = importar_pelicula_tmdb(tmdb_id)
        
        if not response['success']:
            messages.error(request, f'Error: {response.get("error")}')
            return redirect('admin:peliculas_pelicula_change', pelicula_id)
        
        data = response['data']
        
        # Actualizar campos vacíos o si el usuario lo confirma
        campos_actualizados = []
        
        if not pelicula.sinopsis and data.get('sinopsis'):
            pelicula.sinopsis = data['sinopsis']
            campos_actualizados.append('sinopsis')
        
        if not pelicula.duracion and data.get('duracion'):
            pelicula.duracion = data['duracion']
            campos_actualizados.append('duración')
        
        if not pelicula.director and data.get('director'):
            pelicula.director = data['director']
            campos_actualizados.append('director')
        
        if not pelicula.actores and data.get('actores'):
            pelicula.actores = data['actores']
            campos_actualizados.append('actores')
        
        if not pelicula.año and data.get('año'):
            pelicula.año = data['año']
            campos_actualizados.append('año')
        
        if not pelicula.genero and data.get('genero'):
            pelicula.genero = data['genero']
            campos_actualizados.append('género')
        
        # NUEVO: Descargar poster si no tiene
        if not pelicula.poster and data.get('poster_url'):
            try:
                poster_file = descargar_poster(data['poster_url'], pelicula.titulo)
                if poster_file:
                    pelicula.poster.save(poster_file.name, poster_file, save=False)
                    campos_actualizados.append('poster')
            except Exception as e:
                print(f"Error descargando poster: {e}")

        if campos_actualizados:
            pelicula.save()
            messages.success(
                request,
                f'✅ Película actualizada. Campos completados: {", ".join(campos_actualizados)}'
            )
        else:
            messages.info(request, 'No había campos vacíos para actualizar.')
        
        return redirect('admin:peliculas_pelicula_change', pelicula_id)
    
    # GET: Mostrar formulario de búsqueda
    return redirect('admin:peliculas_pelicula_change', pelicula_id)