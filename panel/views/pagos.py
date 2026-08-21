# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

# modificado (T6 - BI): + Count (distribución por método de pago) y
# CuponUsado (solo lectura, para el ROI de cupones — el modelo Cupon vive
# en la app promociones, no se toca nada ahí).
from datetime import timedelta
from django.db.models import Sum, Q, Count
from django.shortcuts import render
from django.utils import timezone
from pagos.models import Pago
from promociones.models import CuponUsado
from salas.models import Funcion
from ..decorators import staff_required, get_sede_activa_panel


# ============================================================
# PAGOS
# ============================================================

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
    roi_cupones = _roi_cupones(sede_activa)
    metodo_pago = _distribucion_metodo_pago(sede_activa)

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
    }
    return render(request, 'panel/pagos/estadisticas.html', contexto)


# ============================================================
# nuevo (T6 - BI): ROI de cupones + distribución por método de pago
# ============================================================

def _roi_cupones(sede=None):
    """
    Por cada cupón usado: cuánto descuento otorgó en total
    (descuento_total_otorgado, de CuponUsado.descuento_aplicado) vs.
    cuánta recaudación generaron los pagos APROBADOS de esas reservas
    (recaudacion_generada, de Pago.monto vía CuponUsado.reserva).

    nuevo (T6 - BI): cupones_estadisticas() ya vive en
    panel/views/promociones.py — fuera del alcance de esta tanda, no se
    toca — y calcula usos/descuentos, pero no compara contra la
    recaudación generada; eso es lo que agrega este cálculo, en modo
    lectura sobre CuponUsado/Cupon (ambos de la app promociones).

    Una reserva con cupón que nunca se pagó (o cuyo pago fue rechazado)
    no suma a 'recaudacion_generada' porque se filtra
    reserva__pago__estado='aprobado'; reservas sin pago asociado quedan
    afuera directamente (join implícito de Django).
    """
    filtro_sede = {'reserva__funcion__sala__sede': sede} if sede else {}
    datos = CuponUsado.objects.filter(
        reserva__isnull=False,
        reserva__pago__estado='aprobado',
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


def _distribucion_metodo_pago(sede=None):
    """
    Distribución de pagos APROBADOS por método de pago (torta), sobre el
    total histórico.

    nuevo (T6 - BI): a diferencia de panel/views/dashboard.py, esta vista
    (pagos.py) no tiene hoy un selector de rango de fechas — trabaja con
    'hoy' y 'total histórico' (ver pagos_estadisticas() arriba). El
    paquete T6_thomp.md pide graficar "para el rango de fechas ya
    filtrado en pagos.py", pero ese rango no existe todavía acá; se deja
    explícito: esta distribución es sobre el total histórico, mismo
    alcance que 'total_recaudado'. Si más adelante se agrega un filtro de
    fechas a pagos.py, este cálculo debería recibir desde/hasta como
    parámetros, igual que los helpers de dashboard.py.
    """
    filtro_sede = {'reserva__funcion__sala__sede': sede} if sede else {}
    datos = Pago.objects.filter(
        estado='aprobado', **filtro_sede
    ).values('metodo_pago').annotate(cantidad=Count('id')).order_by('-cantidad')

    metodo_label = dict(Pago.METODO_PAGO_CHOICES)
    labels = [metodo_label.get(d['metodo_pago'], d['metodo_pago']) for d in datos]
    valores = [d['cantidad'] for d in datos]
    return {'labels': labels, 'valores': valores}


