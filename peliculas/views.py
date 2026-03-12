from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Q
from .models import Pelicula

def inicio(request):
    return render(request, 'inicio.html')

def lista_peliculas(request):
    # Obtener todas las películas en cartelera
    peliculas = Pelicula.objects.filter(en_cartelera=True)
    
    # BÚSQUEDA por título (solo si existe)
    busqueda = request.GET.get('buscar', '')
    if busqueda:
        # Búsqueda solo en campos que existen
        query = Q(titulo__icontains=busqueda)
        
        # Agregar búsqueda en director si el campo existe
        if hasattr(Pelicula, 'director') and Pelicula._meta.get_field('director'):
            query |= Q(director__icontains=busqueda)
        
        # Agregar búsqueda en actores si el campo existe
        if hasattr(Pelicula, 'actores') and Pelicula._meta.get_field('actores'):
            query |= Q(actores__icontains=busqueda)
        
        peliculas = peliculas.filter(query)
    
    # FILTRO por género
    genero = request.GET.get('genero', '')
    if genero:
        peliculas = peliculas.filter(genero=genero)
    
    # FILTRO por clasificación
    clasificacion = request.GET.get('clasificacion', '')
    if clasificacion:
        peliculas = peliculas.filter(clasificacion=clasificacion)
    
    # ORDEN
    orden = request.GET.get('orden', 'titulo')
    if orden == 'titulo':
        peliculas = peliculas.order_by('titulo')
    elif orden == 'año':
        # Solo ordenar por año si el campo existe
        if hasattr(Pelicula, 'año'):
            peliculas = peliculas.order_by('-año', 'titulo')
        else:
            peliculas = peliculas.order_by('titulo')
    elif orden == 'genero':
        peliculas = peliculas.order_by('genero', 'titulo')
    
    # Obtener opciones para los filtros
    generos_disponibles = Pelicula.GENERO_CHOICES
    clasificaciones_disponibles = Pelicula.CLASIFICACION_CHOICES
    
    contexto = {
        'peliculas': peliculas,
        'busqueda': busqueda,
        'genero_seleccionado': genero,
        'clasificacion_seleccionada': clasificacion,
        'orden_seleccionado': orden,
        'generos_disponibles': generos_disponibles,
        'clasificaciones_disponibles': clasificaciones_disponibles,
        'total_resultados': peliculas.count(),
    }
    return render(request, 'peliculas/lista_pelis.html', contexto)

def detalle_pelicula(request, pelicula_id):
    pelicula = get_object_or_404(Pelicula, id=pelicula_id)
    # Obtener solo funciones disponibles y futuras para esta película
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