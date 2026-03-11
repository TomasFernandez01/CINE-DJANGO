from .models import Pelicula
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

def inicio(request):
    return render(request, 'inicio.html')

def lista_peliculas(request):
    peliculas = Pelicula.objects.all()
    contexto = {
        'peliculas': peliculas
    }
    return render(request, 'peliculas/lista_pelis.html', contexto)

# def detalle_pelicula(request, pelicula_id):
#     pelicula = get_object_or_404(Pelicula, id=pelicula_id)
#     # Obtener funciones disponibles para esta película
#     funciones = pelicula.funciones.filter(disponible=True).select_related('sala').order_by('fecha_hora')
    
#     contexto = {
#         'pelicula': pelicula,
#         'funciones': funciones,
#     }
#     return render(request, 'detalle_pelicula.html', contexto)

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