# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from datetime import timedelta
from django.db.models import Sum, Count
from django.shortcuts import render
from django.utils import timezone
from pagos.models import Pago
from peliculas.models import Pelicula
from promociones.models import CuponUsado
from reservas.models import Reserva
from salas.models import Funcion
from ..decorators import staff_required, get_sede_activa_panel


# ============================================================
# DASHBOARD PRINCIPAL
# ============================================================

# MODIFICACION GEMINI: Dashboard con datos para graficos de recaudacion y promociones
@staff_required
def inicio(request):
    ahora = timezone.now()
    hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    semana = hoy - timedelta(days=7)

    # nuevo (Sedes - Fase 3): filtros base a encadenar en cada query de
    # esta vista, según la sede activa del staff (fija o elegida). No se
    # filtra Pelicula: el catálogo sigue siendo compartido entre sedes
    # (una función de esa película sí pertenece a una sede puntual).
    sede_activa = get_sede_activa_panel(request)
    filtro_funcion = {'sala__sede': sede_activa} if sede_activa else {}
    filtro_reserva = {'funcion__sala__sede': sede_activa} if sede_activa else {}
    filtro_pago = {'reserva__funcion__sala__sede': sede_activa} if sede_activa else {}
    filtro_cupon_usado = {'reserva__funcion__sala__sede': sede_activa} if sede_activa else {}

    # Tarjetas de resumen
    stats = {
        'peliculas_cartelera': Pelicula.objects.filter(en_cartelera=True).count(),
        'peliculas_total': Pelicula.objects.count(),
        'funciones_hoy': Funcion.objects.filter(
            fecha_hora__gte=hoy,
            fecha_hora__lt=hoy + timedelta(days=1),
            disponible=True,
            **filtro_funcion
        ).count(),
        'funciones_proximas': Funcion.objects.filter(
            fecha_hora__gte=ahora, disponible=True, **filtro_funcion
        ).count(),
        'reservas_pendientes': Reserva.objects.filter(estado='pendiente', **filtro_reserva).count(),
        'reservas_hoy': Reserva.objects.filter(fecha_reserva__gte=hoy, **filtro_reserva).count(),
        'reservas_confirmadas_hoy': Reserva.objects.filter(
            estado='confirmada', fecha_reserva__gte=hoy, **filtro_reserva
        ).count(),
        'recaudado_hoy': Pago.objects.filter(
            estado='aprobado', fecha_pago__gte=hoy, **filtro_pago
        ).aggregate(t=Sum('monto'))['t'] or 0,
        'recaudado_semana': Pago.objects.filter(
            estado='aprobado', fecha_pago__gte=semana, **filtro_pago
        ).aggregate(t=Sum('monto'))['t'] or 0,
        'qr_escaneados_hoy': Pago.objects.filter(
            qr_escaneado=True, fecha_escaneo__gte=hoy, **filtro_pago
        ).count(),
    }

    # MODIFICACION GEMINI: Calculo de recaudacion ultimos 7 dias para grafico
    chart_recaudacion_valores = []
    chart_recaudacion_labels = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        monto_dia = Pago.objects.filter(
            estado='aprobado',
            fecha_pago__date=dia.date(),
            **filtro_pago
        ).aggregate(t=Sum('monto'))['t'] or 0
        chart_recaudacion_valores.append(float(monto_dia))
        chart_recaudacion_labels.append(dia.strftime('%d/%m'))

    # MODIFICACION GEMINI: Estadisticas de combos vendidos para grafico
    top_combos = Pago.objects.filter(estado='aprobado', **filtro_pago).exclude(combo=None).values(
        'combo__nombre'
    ).annotate(
        cantidad=Sum('cantidad_combo')
    ).order_by('-cantidad')[:5]
    
    chart_combos_labels = [c['combo__nombre'] for c in top_combos]
    chart_combos_valores = [c['cantidad'] for c in top_combos]

    # MODIFICACION GEMINI: Estadisticas de cupones mas usados para grafico
    top_cupones = CuponUsado.objects.filter(**filtro_cupon_usado).values(
        'cupon__codigo'
    ).annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')[:5]

    chart_cupones_labels = [c['cupon__codigo'] for c in top_cupones]
    chart_cupones_valores = [c['cantidad'] for c in top_cupones]

    # Próximas funciones (hoy y mañana)
    proximas_funciones = Funcion.objects.filter(
        fecha_hora__gte=ahora,
        fecha_hora__lt=hoy + timedelta(days=2),
        disponible=True,
        **filtro_funcion
    ).select_related('pelicula', 'sala').order_by('fecha_hora')[:8]

    # Últimas reservas
    ultimas_reservas = Reserva.objects.filter(**filtro_reserva).select_related(
        'usuario', 'funcion__pelicula'
    ).order_by('-fecha_reserva')[:8]

    # Últimos pagos
    ultimos_pagos = Pago.objects.filter(
        estado='aprobado', **filtro_pago
    ).select_related(
        'reserva__usuario', 'reserva__funcion__pelicula'
    ).order_by('-fecha_pago')[:5]

    contexto = {
        'stats': stats,
        'proximas_funciones': proximas_funciones,
        'ultimas_reservas': ultimas_reservas,
        'ultimos_pagos': ultimos_pagos,
        'seccion_activa': 'inicio',
        # MODIFICACION GEMINI: pasar datos para graficos al template
        'chart_recaudacion_valores': chart_recaudacion_valores,
        'chart_recaudacion_labels': chart_recaudacion_labels,
        'chart_combos_labels': chart_combos_labels,
        'chart_combos_valores': chart_combos_valores,
        'chart_cupones_labels': chart_cupones_labels,
        'chart_cupones_valores': chart_cupones_valores,
    }
    return render(request, 'panel/inicio.html', contexto)


