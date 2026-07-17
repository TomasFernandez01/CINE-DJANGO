from django.shortcuts import render
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Sala, Funcion
from peliculas.models import Pelicula
from utils.fechas import generar_proximos_dias  # nuevo: helper compartido del carrusel de fechas

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
    ).select_related('pelicula', 'sala')
    
    # FILTRO por película
    pelicula_id = request.GET.get('pelicula', '')
    if pelicula_id:
        funciones = funciones.filter(pelicula_id=pelicula_id)
    
    # FILTRO por fecha
    fecha_filtro = request.GET.get('fecha', '')
    if fecha_filtro == 'hoy':
        hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        hoy_fin = hoy_inicio + timedelta(days=1)
        funciones = funciones.filter(fecha_hora__gte=hoy_inicio, fecha_hora__lt=hoy_fin)
    elif fecha_filtro == 'mañana':
        mañana_inicio = (ahora + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        mañana_fin = mañana_inicio + timedelta(days=1)
        funciones = funciones.filter(fecha_hora__gte=mañana_inicio, fecha_hora__lt=mañana_fin)
    elif fecha_filtro == 'semana':
        semana_fin = ahora + timedelta(days=7)
        funciones = funciones.filter(fecha_hora__lte=semana_fin)
    elif fecha_filtro:  # Fecha específica en formato YYYY-MM-DD
        try:
            fecha_especifica = datetime.strptime(fecha_filtro, '%Y-%m-%d')
            fecha_inicio = fecha_especifica.replace(hour=0, minute=0, second=0, microsecond=0)
            fecha_fin = fecha_inicio + timedelta(days=1)
            funciones = funciones.filter(fecha_hora__gte=fecha_inicio, fecha_hora__lt=fecha_fin)
        except ValueError:
            pass
    
    # FILTRO por sala
    sala_id = request.GET.get('sala', '')
    if sala_id:
        funciones = funciones.filter(sala_id=sala_id)
    
    # ORDEN
    orden = request.GET.get('orden', 'fecha')
    if orden == 'fecha':
        funciones = funciones.order_by('fecha_hora')
    elif orden == 'precio':
        funciones = funciones.order_by('precio', 'fecha_hora')
    elif orden == 'pelicula':
        funciones = funciones.order_by('pelicula__titulo', 'fecha_hora')
    
    # Obtener opciones para los filtros
    peliculas_con_funciones = Pelicula.objects.filter(
        funciones__disponible=True,
        funciones__fecha_hora__gt=ahora
    ).distinct().order_by('titulo')
    
    salas_con_funciones = Sala.objects.filter(
        funciones__disponible=True,
        funciones__fecha_hora__gt=ahora
    ).distinct().order_by('nombre')
    
    contexto = {
        'funciones': funciones,
        'peliculas_disponibles': peliculas_con_funciones,
        'salas_disponibles': salas_con_funciones,
        'pelicula_seleccionada': pelicula_id,
        'fecha_seleccionada': fecha_filtro,
        'sala_seleccionada': sala_id,
        'orden_seleccionado': orden,
        'total_resultados': funciones.count(),
        'proximas_fechas': generar_proximos_dias(20),  # nuevo: carrusel de fechas de esta pagina
    }
    return render(request, 'salas/lista_funciones.html', contexto)