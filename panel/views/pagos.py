# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from datetime import timedelta
from django.db.models import Sum, Q
from django.shortcuts import render
from django.utils import timezone
from pagos.models import Pago
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
    }
    return render(request, 'panel/pagos/estadisticas.html', contexto)


