from django.shortcuts import render
from .models import Sala, Funcion

def lista_salas(request):
    salas = Sala.objects.filter(activa=True)
    contexto = {
        'salas': salas
    }
    return render(request, 'salas/lista_salas.html', contexto)

def lista_funciones(request):
    funciones = Funcion.objects.filter(disponible=True).select_related('pelicula', 'sala')
    contexto = {
        'funciones': funciones
    }
    return render(request, 'salas/lista_funciones.html', contexto)