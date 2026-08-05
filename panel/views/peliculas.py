# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from django.contrib import messages
from django.core.files.base import ContentFile
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from pagos.models import Pago
from peliculas.models import Pelicula
from reservas.models import Reserva
import requests
from ..decorators import staff_required
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

@staff_required
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
            messages.success(request, f'✅ Película "{pelicula.titulo}" creada exitosamente.')
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
        # Si Validacion falla y formulario lo rellena TMDB (trae el campo oculto poster_url_tmdb en el POST), lo re-pasamos al contexto para no perder la preview del poster al re-renderizar.
        'poster_url_tmdb': request.POST.get('poster_url_tmdb', '') if request.method == 'POST' else '',
    })


@staff_required
def peliculas_editar(request, pelicula_id):
    pelicula = get_object_or_404(Pelicula, id=pelicula_id)

    if request.method == 'POST':
        form = PeliculaForm(request.POST, request.FILES, instance=pelicula)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Película "{pelicula.titulo}" actualizada.')
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
    })

@staff_required
@require_POST
def peliculas_eliminar(request):
    """
    Borrado múltiple de películas, en dos pasos (mismo patrón que salas_eliminar):
      1. Sin 'confirmado': vista previa con cuántas funciones, reservas y pagos
         se van a borrar en cascada (Pelicula -> Funcion -> Reserva -> Pago).
      2. Con 'confirmado=1': borra de verdad.
    """
    ids = request.POST.getlist('seleccionadas')
    if not ids:
        messages.error(request, 'No seleccionaste ninguna película.')
        return redirect('panel:peliculas_lista')

    peliculas_qs = Pelicula.objects.filter(id__in=ids)
    if not peliculas_qs.exists():
        messages.error(request, 'Las películas seleccionadas ya no existen.')
        return redirect('panel:peliculas_lista')

    if request.POST.get('confirmado') == '1':
        titulos = list(peliculas_qs.values_list('titulo', flat=True))
        peliculas_qs.delete()  # cascada: borra también sus funciones, reservas y pagos
        messages.success(request, f'🗑️ Película(s) eliminada(s): {", ".join(titulos)}.')
        return redirect('panel:peliculas_lista')

    # Paso 1: vista previa de lo que se va a borrar en cascada
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

    return render(request, 'panel/peliculas/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
        'seccion_activa': 'peliculas',
    })
# ============================================================
# PELÍCULAS — T M D B
# ============================================================

@staff_required
def peliculas_buscar_tmdb(request):
    """Búsqueda TMDB integrada en el panel."""
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


@staff_required
def peliculas_importar_tmdb(request, tmdb_id):
    """
    Importa una película desde TMDB y redirige al formulario de edición. Precarga datos en el formulario (accion='crear'), SIN guardar en BD. El poster no se puede precargar en un <input type="file">, así que se muestra como preview y se pasa la URL original en un campo oculto: si el usuario no sube un poster propio, recién al guardar (en peliculas_crear) se descarga esa imagen.
    """
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
# PELÍCULAS
# ============================================================

@staff_required
def peliculas_lista(request):
    busqueda = request.GET.get('q', '')
    en_cartelera = request.GET.get('cartelera', '')

    peliculas = Pelicula.objects.all()
    if busqueda:
        peliculas = peliculas.filter(
            Q(titulo__icontains=busqueda) | Q(director__icontains=busqueda)
        )
    if en_cartelera == 'si':
        peliculas = peliculas.filter(en_cartelera=True)
    elif en_cartelera == 'no':
        peliculas = peliculas.filter(en_cartelera=False)

    peliculas = peliculas.order_by('-en_cartelera', 'titulo')
    
    # MODIFICACION GEMINI: Paginacion en la lista de peliculas del panel (8 por pagina)
    from django.core.paginator import Paginator
    paginator = Paginator(peliculas, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    contexto = {
        'peliculas': page_obj,
        'page_obj': page_obj,
        'busqueda': busqueda,
        'en_cartelera': en_cartelera,
        'total': peliculas.count(),
        'seccion_activa': 'peliculas',
    }
    return render(request, 'panel/peliculas/lista.html', contexto)
    contexto = {
        'peliculas': peliculas,
        'busqueda': busqueda,
        'en_cartelera': en_cartelera,
        'total': peliculas.count(),
        'seccion_activa': 'peliculas',
    }
    return render(request, 'panel/peliculas/lista.html', contexto)


@staff_required
def peliculas_detalle(request, pelicula_id):
    pelicula = get_object_or_404(Pelicula, id=pelicula_id)
    ahora = timezone.now()
    funciones = pelicula.funciones.filter(
        fecha_hora__gte=ahora
    ).select_related('sala').order_by('fecha_hora')
    
    # MODIFICACION GEMINI: Obtener calificaciones para el panel admin
    ratings = pelicula.ratings.all().select_related('usuario').order_by('-fecha_creacion')

    contexto = {
        'pelicula': pelicula,
        'funciones': funciones,
        'ratings': ratings,
        'seccion_activa': 'peliculas',
    }
    return render(request, 'panel/peliculas/detalle.html', contexto)


