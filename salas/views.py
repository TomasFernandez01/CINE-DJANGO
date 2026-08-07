from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Sala, Funcion
from peliculas.models import Pelicula
from utils.fechas import generar_proximos_dias  
from utils.funciones import agrupar_por_tipo_sala  

def lista_salas(request):
    
    salas = Sala.objects.filter(activa=True).prefetch_related('bloqueos_asientos', 'categorias_asientos')
    for sala in salas:
        sala.mapa_layout = sala.layout_asientos()
        sala.mapa_bloqueados = {
            b.asiento_codigo for b in sala.bloqueos_asientos.all() if b.funcion_id is None
        }
        sala.mapa_categoria = {c.asiento_codigo for c in sala.categorias_asientos.all()}
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
        
    # MEJORAS/REDISEÑO GEMINI: Filtro de búsqueda en vivo por película
    buscar_peli = request.GET.get('buscar', '').strip()
    if buscar_peli:
        funciones = funciones.filter(
            Q(pelicula__titulo__icontains=buscar_peli) |
            Q(pelicula__director__icontains=buscar_peli) |
            Q(pelicula__actores__icontains=buscar_peli)
        )
    
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
    # (tanda 3): se agrupan las funciones por pelicula. se reutiliza helper de detalle_pelicula para agrupar por tipo de sala. El orden 'fecha' respeta el orden de aparicion (la pelicula con la funcion mas proxima aparece primero, porque 'funciones' ya viene ordenado por fecha_hora salvo que se haya elegido otro orden arriba).
    peliculas_agrupadas = {}
    orden_aparicion = []
    for funcion in funciones:
        pid = funcion.pelicula_id
        if pid not in peliculas_agrupadas:
            peliculas_agrupadas[pid] = {'pelicula': funcion.pelicula, 'funciones': []}
            orden_aparicion.append(pid)
        peliculas_agrupadas[pid]['funciones'].append(funcion)

    tarjetas_peliculas = []
    for pid in orden_aparicion:
        entrada = peliculas_agrupadas[pid]
        tarjetas_peliculas.append({
            'pelicula': entrada['pelicula'],
            'grupos_funciones': agrupar_por_tipo_sala(entrada['funciones']),
            'precio_desde': min(f.precio_final() for f in entrada['funciones']),
        })

    if orden == 'precio':
        # a nivel tarjeta, "por precio" ordena por el precio mas barato de esa pelicula
        tarjetas_peliculas.sort(key=lambda t: t['precio_desde'])
    
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
        'tarjetas_peliculas': tarjetas_peliculas,  # nuevo (tanda 3): agrupado por pelicula
        'peliculas_disponibles': peliculas_con_funciones,
        'salas_disponibles': salas_con_funciones,
        'pelicula_seleccionada': pelicula_id,
        'fecha_seleccionada': fecha_filtro,
        'sala_seleccionada': sala_id,
        'orden_seleccionado': orden,
        'total_resultados': funciones.count(),
        'proximas_fechas': generar_proximos_dias(20),  # nuevo: carrusel de fechas de esta pagina
        # MEJORAS/REDISEÑO GEMINI: Pasar el texto de búsqueda al contexto
        'busqueda': buscar_peli,
    }
    # MEJORAS/REDISEÑO GEMINI: Retornar solo el partial si es AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == 'true':
        return render(request, 'salas/partials/_lista_funciones_grid.html', contexto)
        
    return render(request, 'salas/lista_funciones.html', contexto)
    