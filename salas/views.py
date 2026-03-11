from django.shortcuts import render
from django.utils import timezone
from .models import Sala, Funcion

def lista_salas(request):
    salas = Sala.objects.filter(activa=True)
    contexto = {
        'salas': salas
    }
    return render(request, 'salas/lista_salas.html', contexto)

def lista_funciones(request):
    # Filtrar solo funciones disponibles y futuras
    ahora = timezone.now()
    funciones = Funcion.objects.filter(
        disponible=True,
        fecha_hora__gt=ahora
    ).select_related('pelicula', 'sala').order_by('fecha_hora')
    
    contexto = {
        'funciones': funciones
    }
    return render(request, 'salas/lista_funciones.html', contexto)