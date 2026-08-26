from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Exists, OuterRef  # modificado (T2): Exists/OuterRef para anotar funciones por sede
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from pagos.models import Pago
from peliculas.models import Pelicula
from reservas.models import Reserva
from salas.models import Funcion  # modificado (T2): para el subquery de funciones por sede
import requests
from ..decorators import staff_required, superuser_required, get_sede_staff  # modificado (T2): get_sede_staff, mismo patrón que funciones.py
from ..forms import (
    PeliculaForm,
)
try:
    from utils.tmdb_api import buscar_pelicula_tmdb, importar_pelicula_tmdb
    TMDB_DISPONIBLE = True
except ImportError:
    TMDB_DISPONIBLE = False


# ============================================================
# PELÍCULAS — CRUD
# ============================================================

# MODIFICACION GEMINI: Crear películas es función exclusiva del SuperUser (Corporate HQ)
@superuser_required
def peliculas_crear(request):
    if request.method == 'POST':
        form = PeliculaForm(request.POST, request.FILES)
        if form.is_valid():
            pelicula = form.save()
            poster_url_tmdb = request.POST.get('poster_url_tmdb', '').strip()
            if poster_url_tmdb and not pelicula.poster:
                try:
                    resp = requests.get(poster_url_tmdb, timeout=10)
                    resp.raise_for_status()
                    nombre = f"{pelicula.titulo.lower().replace(' ', '_')[:40]}.jpg"
                    pelicula.poster.save(nombre, ContentFile(resp.content), save=True)
                except Exception:
                    pass 
            messages.success(request, f'Película "{pelicula.titulo}" creada exitosamente.')
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:peliculas_crear')
            return redirect('panel:peliculas_detalle', pelicula_id=pelicula.id)
    else:
        form = PeliculaForm()

    return render(request, 'panel/peliculas/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Película',
        'accion': 'crear',
        'seccion_activa': 'peliculas',
        'poster_url_tmdb': request.POST.get('poster_url_tmdb', '') if request.method == 'POST' else '',
    })


@staff_required
def peliculas_editar(request, pelicula_id):
    pelicula = get_object_or_404(Pelicula, id=pelicula_id)
    es_super = request.user.is_superuser

    if request.method == 'POST':
        form = PeliculaForm(request.POST, request.FILES, instance=pelicula)
        
        # MODIFICACION GEMINI: Si es Staff (no SuperUser), solo se permite alterar en_cartelera y fecha_estreno
        # modificado (Hilo 4 - Claude): TODO de T2 resuelto. en_cartelera es un
        # campo GLOBAL (afecta el sitio público entero, todas las sedes a la
        # vez: peliculas/views.py::inicio y lista_peliculas filtran por
        # en_cartelera=True sin distinguir sede). Dejar que un Staff de UNA
        # sede lo apague de golpe sacaba la película de la cartelera pública
        # de TODAS las sedes, no solo la suya -- exactamente el problema que
        # señalaba el TODO. Resolución elegida: Staff ya NO controla
        # en_cartelera (pasa a ser exclusivo de SuperUser, mismo criterio que
        # el resto de los campos globales de Pelicula). El indicador real de
        # "en cartelera en MI sede" para Staff no necesita un campo propio:
        # ya se resuelve solo, sin acción manual, a partir de si existen
        # Funcion en su sede (ver peliculas_lista más abajo,
        # tiene_funciones_en_mi_sede) -- que es justamente lo que Staff sí
        # controla creando/borrando funciones para su sede. Fecha de estreno
        # sigue siendo editable por Staff (no tiene el mismo problema: es
        # informativo, no filtra nada en el sitio público).
        if not es_super:
            # Preservar valores originales de los demás campos
            if form.is_valid():
                obj = form.save(commit=False)
                original = Pelicula.objects.get(id=pelicula.id)
                obj.titulo = original.titulo
                obj.sinopsis = original.sinopsis
                obj.duracion = original.duracion
                obj.genero = original.genero
                obj.clasificacion = original.clasificacion
                obj.director = original.director
                obj.actores = original.actores
                obj.año = original.año
                obj.poster = original.poster
                obj.en_cartelera = original.en_cartelera  # modificado (Hilo 4): ver comentario arriba
                obj.save()
                messages.success(request, f'Película "{pelicula.titulo}" actualizada (activación/estreno por Staff).')
                return redirect('panel:peliculas_detalle', pelicula_id=pelicula.id)
        else:
            if form.is_valid():
                form.save()
                messages.success(request, f'Película "{pelicula.titulo}" actualizada completamente por SuperUser.')
                if request.POST.get('guardar_y_agregar_otro'):
                    return redirect('panel:peliculas_crear')
                return redirect('panel:peliculas_detalle', pelicula_id=pelicula.id)
    else:
        form = PeliculaForm(instance=pelicula)

    return render(request, 'panel/peliculas/form.html', {
        'form': form,
        'objeto': pelicula,
        'titulo_pagina': f'Editar: {pelicula.titulo}',
        'accion': 'editar',
        'seccion_activa': 'peliculas',
        'es_super': es_super,
    })

# MODIFICACION GEMINI: Eliminación de películas exclusiva para SuperUser
@superuser_required
@require_POST
def peliculas_eliminar(request):
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    ids = request.POST.getlist('seleccionadas')
    if not ids:
        if es_ajax:
            return JsonResponse({'error': 'No seleccionaste ninguna película.'}, status=400)
        messages.error(request, 'No seleccionaste ninguna película.')
        return redirect('panel:peliculas_lista')

    peliculas_qs = Pelicula.objects.filter(id__in=ids)
    if not peliculas_qs.exists():
        if es_ajax:
            return JsonResponse({'error': 'Las películas seleccionadas ya no existen.'}, status=400)
        messages.error(request, 'Las películas seleccionadas ya no existen.')
        return redirect('panel:peliculas_lista')

    if request.POST.get('confirmado') == '1':
        titulos = list(peliculas_qs.values_list('titulo', flat=True))
        peliculas_qs.delete()
        messages.success(request, f'Película(s) eliminada(s): {", ".join(titulos)}.')
        if es_ajax:
            return JsonResponse({'success': True})
        return redirect('panel:peliculas_lista')

    resumen = []
    for pelicula in peliculas_qs:
        total_funciones = pelicula.funciones.count()
        total_reservas = Reserva.objects.filter(funcion__pelicula=pelicula).count()
        total_pagos = Pago.objects.filter(reserva__funcion__pelicula=pelicula).count()
        resumen.append({
            'pelicula': pelicula,
            'total_funciones': total_funciones,
            'total_reservas': total_reservas,
            'total_pagos': total_pagos,
        })

    if es_ajax:
        lineas = [
            f'{item["pelicula"].titulo}: {item["total_funciones"]} función(es), '
            f'{item["total_reservas"]} reserva(s), {item["total_pagos"]} pago(s)'
            for item in resumen
        ]
        return JsonResponse({
            'lineas': lineas,
            'advertencia': ('Esta acción no se puede deshacer. Al borrar una película, '
                             'también se borran en cascada sus funciones, las reservas '
                             'de esas funciones y los pagos asociados.'),
        })

    return render(request, 'panel/peliculas/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
        'seccion_activa': 'peliculas',
    })

# ============================================================
# PELÍCULAS — T M D B (Exclusivo SuperUser)
# ============================================================

@superuser_required
def peliculas_buscar_tmdb(request):
    resultados = []
    query = ''

    if request.method == 'GET' and 'q' in request.GET:
        query = request.GET.get('q', '').strip()
        if query and TMDB_DISPONIBLE:
            response = buscar_pelicula_tmdb(query)
            if response['success']:
                resultados = response['results']
                if not resultados:
                    messages.info(request, f'Sin resultados para "{query}"')
            else:
                messages.error(request, f'Error al buscar: {response.get("error")}')

    return render(request, 'panel/peliculas/buscar_tmdb.html', {
        'query': query,
        'resultados': resultados,
        'tmdb_disponible': TMDB_DISPONIBLE,
        'seccion_activa': 'peliculas',
    })


@superuser_required
def peliculas_importar_tmdb(request, tmdb_id):
    if not TMDB_DISPONIBLE:
        messages.error(request, 'TMDB no está configurado.')
        return redirect('panel:peliculas_buscar_tmdb')

    response = importar_pelicula_tmdb(tmdb_id)
    if not response['success']:
        messages.error(request, f'Error: {response.get("error")}')
        return redirect('panel:peliculas_buscar_tmdb')

    data = response['data']

    existente = Pelicula.objects.filter(titulo__iexact=data['titulo']).first()
    if existente:
        messages.warning(request, f'"{data["titulo"]}" ya existe. Podés editarla.')
        return redirect('panel:peliculas_editar', pelicula_id=existente.id)
    
    form = PeliculaForm(initial={
        'titulo': data['titulo'][:50],
        'sinopsis': data.get('sinopsis', ''),
        'duracion': data.get('duracion'),
        'genero': data.get('genero'),
        'clasificacion': data.get('clasificacion', 'ATP'),
        'director': data.get('director', ''),
        'actores': data.get('actores', ''),
        'año': data.get('año'),
    })

    messages.info(request, f'Datos de "{data["titulo"]}" importados desde TMDB. Revisá y guardá para crearla.')

    return render(request, 'panel/peliculas/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Película (desde TMDB)',
        'accion': 'crear',
        'seccion_activa': 'peliculas',
        'poster_url_tmdb': data.get('poster_url', ''),
    })

# ============================================================
# PELÍCULAS LISTA Y ANALÍTICA
# ============================================================

@staff_required
def peliculas_lista(request):
    busqueda = request.GET.get('q', '')
    en_cartelera = request.GET.get('cartelera', '')
    es_super = request.user.is_superuser  # modificado (T2): calculado antes para decidir el anotado por sede

    peliculas = Pelicula.objects.all()
    if busqueda:
        peliculas = peliculas.filter(
            Q(titulo__icontains=busqueda) | Q(director__icontains=busqueda)
        )
    if en_cartelera == 'si':
        peliculas = peliculas.filter(en_cartelera=True)
    elif en_cartelera == 'no':
        peliculas = peliculas.filter(en_cartelera=False)

    # modificado (T2 - Visibilidad por sede): NO se filtra el catálogo (el
    # Staff sigue viendo todas las películas, igual que antes), pero si es
    # Staff con sede fija asignada se ANOTA cada película con si tiene o no
    # funciones programadas en su sede. Mismo patrón que get_sede_staff() ya
    # usa en panel/views/funciones.py (_filtro_sede) — no se filtra por
    # completo el listado porque el Staff puede necesitar ver el catálogo
    # entero para decidir qué programar en su sede.
    sede_staff = None
    if not es_super:
        sede_staff = get_sede_staff(request.user)
        if sede_staff is not None:
            funciones_en_mi_sede = Funcion.objects.filter(
                pelicula=OuterRef('pk'),
                sala__sede=sede_staff,
            )
            peliculas = peliculas.annotate(
                tiene_funciones_en_mi_sede=Exists(funciones_en_mi_sede)
            )

    peliculas = peliculas.order_by('-en_cartelera', 'titulo')

    # MODIFICACION GEMINI: Analítica contextual para el dashboard de películas (Top Títulos y Géneros)
    top_peliculas_stats = Pelicula.objects.annotate(
        total_reservas_confirmadas=Count(
            'funciones__reservas',
            filter=Q(funciones__reservas__estado='confirmada')
        ),
        # modificado: 'total' es un método Python de Reserva, no un campo de BD.
        # El monto pagado real está en Pago.monto (related_name='pago' desde Reserva).
        # Causaba FieldError "Unsupported lookup 'total' for BigAutoField...".
        recaudacion_estimada=Sum(
            'funciones__reservas__pago__monto',  # modificado
            filter=Q(funciones__reservas__estado='confirmada')
        )
    ).order_by('-total_reservas_confirmadas')[:5]

    generos_stats = Pelicula.objects.values('genero').annotate(
        total=Count('id')
    ).order_by('-total')

    paginator = Paginator(peliculas, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    contexto = {
        'peliculas': page_obj,
        'page_obj': page_obj,
        'busqueda': busqueda,
        'en_cartelera': en_cartelera,
        'total': peliculas.count(),
        'top_peliculas_stats': top_peliculas_stats,
        'generos_stats': generos_stats,
        'es_super': es_super,
        'sede_staff': sede_staff,  # modificado (T2): para mostrar el badge "en tu sede" en el template
        'seccion_activa': 'peliculas',
    }
    return render(request, 'panel/peliculas/lista.html', contexto)


@staff_required
def peliculas_detalle(request, pelicula_id):
    pelicula = get_object_or_404(Pelicula, id=pelicula_id)
    ahora = timezone.now()
    funciones = pelicula.funciones.filter(
        fecha_hora__gte=ahora
    ).select_related('sala', 'sala__sede').order_by('fecha_hora')  # modificado (T2): sala__sede para la columna Sede nueva en detalle.html
    
    ratings = pelicula.ratings.all().select_related('usuario').order_by('-fecha_creacion')

    contexto = {
        'pelicula': pelicula,
        'funciones': funciones,
        'ratings': ratings,
        'es_super': request.user.is_superuser,
        'seccion_activa': 'peliculas',
    }
    return render(request, 'panel/peliculas/detalle.html', contexto)



