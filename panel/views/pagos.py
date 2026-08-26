# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

# modificado (T6 - BI): + Count (distribución por método de pago) y
# CuponUsado (solo lectura, para el ROI de cupones — el modelo Cupon vive
# en la app promociones, no se toca nada ahí).
from datetime import date, timedelta  # modificado (Hilo 4 - Claude): date para el filtro desde/hasta
from django.db.models import Sum, Q, Count
from django.shortcuts import render
from django.utils import timezone
from pagos.models import Pago
from promociones.models import CuponUsado
from reservas.models import Reserva  # modificado (T7): solo lectura, para tiempo hasta el pago
from salas.models import Funcion
from ..decorators import staff_required, get_sede_activa_panel


# ============================================================
# PAGOS
# ============================================================

# nuevo (Hilo 4 - Claude): filtro de rango de fechas real, resolviendo el
# punto pendiente que había quedado señalado en el reporte de T6
# ("pagos.py no tiene hoy un selector de rango de fechas"). Mismo formato
# (?desde=YYYY-MM-DD&hasta=YYYY-MM-DD) y mismo criterio de validación que
# ya usa panel/views/dashboard.py::_parsear_rango, pero implementado acá
# como función propia (no se importa de dashboard.py -- son módulos
# hermanos sin dependencia entre sí hoy, y esta función es chica) para no
# crear un acoplamiento entre dos archivos que hasta ahora eran
# independientes. Default: últimos 30 días (mismo default que dashboard.py)
# si no se pasa nada por GET, para que la página no arranque vacía.
def _parsear_rango_pagos(request):
    """Lee ?desde=&hasta= de la request. Devuelve (desde, hasta, error).
    Sin parámetros -> últimos 30 días (hoy incluido). Con error de
    parseo o desde > hasta, devuelve (None, None, mensaje)."""
    desde_raw = request.GET.get('desde', '')
    hasta_raw = request.GET.get('hasta', '')
    if not desde_raw and not hasta_raw:
        hasta = timezone.now().date()
        desde = hasta - timedelta(days=29)
        return desde, hasta, None
    try:
        desde = date.fromisoformat(desde_raw)
        hasta = date.fromisoformat(hasta_raw)
    except ValueError:
        return None, None, "Fechas inválidas. Formato esperado: YYYY-MM-DD."
    if desde > hasta:
        return None, None, "La fecha 'desde' no puede ser posterior a 'hasta'."
    return desde, hasta, None


@staff_required
def pagos_lista(request):
    estado = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')

    pagos = Pago.objects.select_related(
        'reserva__usuario',
        'reserva__funcion__pelicula'
    ).order_by('-fecha_pago')

    # nuevo (Sedes - Fase 3)
    sede_activa = get_sede_activa_panel(request)
    if sede_activa:
        pagos = pagos.filter(reserva__funcion__sala__sede=sede_activa)

    if estado:
        pagos = pagos.filter(estado=estado)
    if busqueda:
        pagos = pagos.filter(
            Q(numero_transaccion__icontains=busqueda) |
            Q(reserva__usuario__username__icontains=busqueda) |
            Q(reserva__codigo_reserva__icontains=busqueda)
        )

    total_filtrado = pagos.aggregate(t=Sum('monto'))['t'] or 0

    contexto = {
        'pagos': pagos[:60],
        'estado': estado,
        'busqueda': busqueda,
        'total_filtrado': total_filtrado,
        'total': pagos.count(),
        'seccion_activa': 'pagos',
    }
    return render(request, 'panel/pagos/lista.html', contexto)


@staff_required
def pagos_estadisticas(request):
    """Las estadísticas viven ahora en el panel."""
    ahora = timezone.now()
    hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    # nuevo (Sedes - Fase 3): filtro base a encadenar en cada query de
    # esta vista, según la sede activa del staff (fija o elegida).
    sede_activa = get_sede_activa_panel(request)
    filtro_pago_sede = {'reserva__funcion__sala__sede': sede_activa} if sede_activa else {}
    filtro_funcion_sede = {'sala__sede': sede_activa} if sede_activa else {}

    # nuevo (Hilo 4 - Claude): rango de fechas real para ROI de cupones y
    # método de pago (ver _parsear_rango_pagos arriba). Si viene mal
    # formado, no se rompe la página entera: se avisa con un mensaje y se
    # cae al default de 30 días, para que "Estadísticas" nunca quede en
    # blanco por un querystring roto.
    desde, hasta, error_rango = _parsear_rango_pagos(request)
    if error_rango:
        hasta = ahora.date()
        desde = hasta - timedelta(days=29)

    pagos_hoy = Pago.objects.filter(estado='aprobado', fecha_pago__gte=hoy, **filtro_pago_sede)
    recaudado_hoy = pagos_hoy.aggregate(t=Sum('monto'))['t'] or 0
    entradas_hoy = pagos_hoy.aggregate(
        t=Sum('reserva__cantidad_entradas')
    )['t'] or 0

    total_recaudado = Pago.objects.filter(
        estado='aprobado', **filtro_pago_sede
    ).aggregate(t=Sum('monto'))['t'] or 0

    qr_escaneados_hoy = Pago.objects.filter(
        qr_escaneado=True, fecha_escaneo__gte=hoy, **filtro_pago_sede
    ).count()
    qr_total = Pago.objects.filter(qr_escaneado=True, **filtro_pago_sede).count()
    qr_pendientes = Pago.objects.filter(
        estado='aprobado',
        qr_escaneado=False,
        reserva__estado='confirmada',
        reserva__funcion__fecha_hora__gte=ahora,
        **filtro_pago_sede
    ).count()

    funciones_hoy = Funcion.objects.filter(
        fecha_hora__gte=hoy,
        fecha_hora__lt=hoy + timedelta(days=1),
        **filtro_funcion_sede
    ).select_related('pelicula', 'sala').order_by('fecha_hora')

    funciones_con_stats = []
    for f in funciones_hoy:
        vendidas = f.reservas.filter(
            estado='confirmada'
        ).aggregate(t=Sum('cantidad_entradas'))['t'] or 0
        cap = f.sala.capacidad
        funciones_con_stats.append({
            'funcion': f,
            'entradas_vendidas': vendidas,
            'capacidad': cap,
            'ocupacion_pct': int(vendidas / cap * 100) if cap else 0,
            'qr_escaneados': Pago.objects.filter(
                reserva__funcion=f, qr_escaneado=True
            ).count(),
        })

    ultimos_pagos = Pago.objects.filter(
        estado='aprobado', **filtro_pago_sede
    ).select_related(
        'reserva__usuario', 'reserva__funcion__pelicula'
    ).order_by('-fecha_pago')[:10]

    ultimos_escaneos = Pago.objects.filter(
        qr_escaneado=True, **filtro_pago_sede
    ).select_related(
        'reserva__usuario',
        'reserva__funcion__pelicula',
        'reserva__funcion__sala'
    ).order_by('-fecha_escaneo')[:10]

    # modificado (T6 - BI): gráfico nuevo #2 (ROI de cupones) y #3
    # (método de pago más usado). Ver helpers al final del archivo.
    # modificado (Hilo 4 - Claude): ambos ahora reciben desde/hasta, ya no
    # son sobre el total histórico fijo (salvo que no se haya pasado
    # ningún parámetro, en cuyo caso el rango es "últimos 30 días" y no
    # "todo el histórico" — ver nota en _distribucion_metodo_pago).
    roi_cupones = _roi_cupones(desde, hasta, sede_activa)
    metodo_pago = _distribucion_metodo_pago(desde, hasta, sede_activa)
    # modificado (T7 - BI): gráfico nuevo #3 (tiempo promedio hasta el pago).
    tiempo_hasta_pago = _tiempo_promedio_hasta_pago(sede_activa)
    
    contexto = {
        'ahora': ahora,
        'recaudado_hoy': recaudado_hoy,
        'entradas_hoy': entradas_hoy,
        'total_recaudado': total_recaudado,
        'qr_escaneados_hoy': qr_escaneados_hoy,
        'qr_total': qr_total,
        'qr_pendientes': qr_pendientes,
        'funciones_con_stats': funciones_con_stats,
        'ultimos_pagos': ultimos_pagos,
        'ultimos_escaneos': ultimos_escaneos,
        'seccion_activa': 'pagos',
        # modificado (T6 - BI)
        'roi_cupones': roi_cupones,
        'metodo_pago_labels': metodo_pago['labels'],
        'metodo_pago_valores': metodo_pago['valores'],
        # modificado (T7 - BI)
        'tiempo_hasta_pago': tiempo_hasta_pago,
        # nuevo (Hilo 4 - Claude): para precargar el form de rango y mostrar
        # el error si el querystring vino mal formado.
        'rango_desde': desde.strftime('%Y-%m-%d'),
        'rango_hasta': hasta.strftime('%Y-%m-%d'),
        'rango_error': error_rango,
    }
    return render(request, 'panel/pagos/estadisticas.html', contexto)


# ============================================================
# nuevo (T6 - BI): ROI de cupones + distribución por método de pago
# ============================================================

def _roi_cupones(desde, hasta, sede=None):
    """
    Por cada cupón usado: cuánto descuento otorgó en total
    (descuento_total_otorgado, de CuponUsado.descuento_aplicado) vs.
    cuánta recaudación generaron los pagos APROBADOS de esas reservas
    (recaudacion_generada, de Pago.monto vía CuponUsado.reserva), dentro
    del rango [desde, hasta] (filtrado por la fecha del PAGO, no la fecha
    en que se usó el cupón, para que el "generó" sea consistente con el
    resto de las métricas de esta página, que también son por fecha_pago).

    nuevo (T6 - BI): cupones_estadisticas() ya vive en
    panel/views/promociones.py — fuera del alcance de esta tanda, no se
    toca — y calcula usos/descuentos, pero no compara contra la
    recaudación generada; eso es lo que agrega este cálculo, en modo
    lectura sobre CuponUsado/Cupon (ambos de la app promociones).

    modificado (Hilo 4 - Claude): antes era sobre el total histórico fijo;
    ahora recibe desde/hasta (ver _parsear_rango_pagos en
    pagos_estadisticas), resolviendo el punto que había quedado señalado
    en el reporte de T6.

    Una reserva con cupón que nunca se pagó (o cuyo pago fue rechazado)
    no suma a 'recaudacion_generada' porque se filtra
    reserva__pago__estado='aprobado'; reservas sin pago asociado quedan
    afuera directamente (join implícito de Django).
    """
    filtro_sede = {'reserva__funcion__sala__sede': sede} if sede else {}
    datos = CuponUsado.objects.filter(
        reserva__isnull=False,
        reserva__pago__estado='aprobado',
        reserva__pago__fecha_pago__date__gte=desde,  # modificado (Hilo 4)
        reserva__pago__fecha_pago__date__lte=hasta,  # modificado (Hilo 4)
        **filtro_sede,
    ).values('cupon__codigo').annotate(
        descuento_total_otorgado=Sum('descuento_aplicado'),
        recaudacion_generada=Sum('reserva__pago__monto'),
    ).order_by('-recaudacion_generada')

    roi = []
    for d in datos:
        descuento = float(d['descuento_total_otorgado'] or 0)
        recaudacion = float(d['recaudacion_generada'] or 0)
        roi.append({
            'codigo': d['cupon__codigo'],
            'descuento_total_otorgado': descuento,
            'recaudacion_generada': recaudacion,
            # ROI = cuánto generó de recaudación por sobre lo que costó en
            # descuento, en % del descuento otorgado. None si el cupón no
            # tuvo descuento registrado (no debería pasar, pero evita
            # división por cero).
            'roi_pct': round((recaudacion - descuento) / descuento * 100, 1) if descuento else None,
        })
    return roi


def _distribucion_metodo_pago(desde, hasta, sede=None):
    """
    Distribución de pagos APROBADOS por método de pago (torta), dentro
    del rango [desde, hasta].

    modificado (Hilo 4 - Claude): resuelve el punto que había quedado
    señalado en el reporte de T6 ("pagos.py no tiene hoy un selector de
    rango de fechas"). Ahora sí lo tiene (ver _parsear_rango_pagos y el
    form en pagos/estadisticas.html) y este cálculo lo recibe como
    parámetro, igual que ya hacían los helpers de dashboard.py.
    """
    filtro_sede = {'reserva__funcion__sala__sede': sede} if sede else {}
    datos = Pago.objects.filter(
        estado='aprobado',
        fecha_pago__date__gte=desde,  # modificado (Hilo 4)
        fecha_pago__date__lte=hasta,  # modificado (Hilo 4)
        **filtro_sede
    ).values('metodo_pago').annotate(cantidad=Count('id')).order_by('-cantidad')

    metodo_label = dict(Pago.METODO_PAGO_CHOICES)
    labels = [metodo_label.get(d['metodo_pago'], d['metodo_pago']) for d in datos]
    valores = [d['cantidad'] for d in datos]
    return {'labels': labels, 'valores': valores}


# ============================================================
# nuevo (T7 - BI): tiempo promedio hasta el pago
# ============================================================

def _tiempo_promedio_hasta_pago(sede=None):
    """
    Promedio de tiempo entre Reserva.fecha_reserva y el momento en que se
    aprobó el pago, para reservas CONFIRMADAS con un Pago APROBADO.

    nuevo (T7): se confirmó en pagos/models.py que Pago NO tiene un campo
    separado tipo 'creado_en' — el único campo de fecha es 'fecha_pago'
    (default=timezone.now), así que se usa ese como "momento del pago".
    No se inventa un campo nuevo.

    Igual que _distribucion_metodo_pago() y _roi_cupones() en este mismo
    archivo, esto es sobre el TOTAL HISTÓRICO (pagos.py no tiene selector
    de rango de fechas hoy — ver nota ya dejada en T6).

    Se descartan diferencias negativas (pago con fecha_pago anterior a
    fecha_reserva) como dato inconsistente en vez de romper el promedio;
    en el proyecto real esto no debería pasar, pero evita que un dato
    corrupto arrastre el promedio para abajo sin que se note.
    """
    filtro_sede = {'funcion__sala__sede': sede} if sede else {}
    reservas = Reserva.objects.filter(
        estado='confirmada',
        pago__isnull=False,
        pago__estado='aprobado',
        **filtro_sede,
    ).select_related('pago')

    minutos_por_reserva = []
    for r in reservas:
        minutos = (r.pago.fecha_pago - r.fecha_reserva).total_seconds() / 60
        if minutos >= 0:
            minutos_por_reserva.append(minutos)

    if not minutos_por_reserva:
        return {'promedio_minutos': None, 'promedio_horas': None, 'cantidad': 0}

    promedio_minutos = sum(minutos_por_reserva) / len(minutos_por_reserva)
    return {
        'promedio_minutos': round(promedio_minutos, 1),
        'promedio_horas': round(promedio_minutos / 60, 1),
        'cantidad': len(minutos_por_reserva),
    }


