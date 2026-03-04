from django.shortcuts import render
from .models import Pelicula

def inicio(request):
    return render(request, 'inicio.html')

def lista_peliculas(request):
    peliculas = Pelicula.objects.all()
    contexto = {
        'peliculas': peliculas
    }
    return render(request, 'peliculas/lista_pelis.html', contexto)