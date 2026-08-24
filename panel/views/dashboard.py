# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

# modificado: reescritura completa del dashboard. Resumen de lo que cambió:
#   - Se sacaron 'proximas_funciones', 'ultimas_reservas' y 'ultimos_pagos'
#     del contexto: ya tienen su propia sección en el Panel (Funciones,
#     Reservas, Pagos) y no aportaban valor de negocio acá.
#   - El gráfico de recaudación de "últimos 7 días fijos" se reemplaza por
#     un gráfico interactivo: el usuario elige fecha desde/hasta y la
#     agrupación (día/semana/mes/bimestre/trimestre/cuatrimestre/anual), y
#     el gráfico se redibuja por AJAX (ver dashboard_grafico_ventas) sin
#     recargar la página. La primera carga ya viene con datos (últimos 30
#     días agrupados por día) para que no se vea vacío antes de que cargue
#     el JS.
#   - El gráfico de combos ahora agrupa por CATEGORÍA (combo/bebida/snack/
#     pochoclo) en vez de por nombre puntual — respondía a "qué comida se
#     consume más", que es una pregunta de categoría, no de producto exacto.
#     Usa el mismo rango de fechas que el gráfico de ventas.
#   - El gráfico de cupones se sacó (no es una métrica de "cuánto se
#     vende", es un dato que ya se puede consultar en Panel > Cupones).
#   - KPIs nuevos con foco en "qué necesita saber el dueño del cine":
#     ticket promedio, comparación vs. el período anterior (mismo largo de
#     días, inmediatamente antes), top 5 películas por recaudación (no por
#     cantidad de funciones — por plata generada), ocupación promedio
#     aproximada, embudo de reservas (pendiente/confirmada/cancelada/
#     expirada) y el día de la semana + horario con más reservas
#     confirmadas.

from datetime import date, timedelta
from django.db.models import Sum, Count, Avg
from django.db.models.functions import ExtractHour, ExtractWeekDay
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from pagos.models import Pago
from peliculas.models import Pelicula
from promociones.models import Combo
from reservas.models import Reserva
from salas.models import Funcion
from utils.fechas import generar_periodos
from ..decorators import staff_required,get_sede_activa_panel

# ExtractWeekDay de Django: 1=Domingo, 2=Lunes, ..., 7=Sábado (¡ojo! no es
# igual a date.weekday(), que arranca en Lunes=0).
DIAS_EXTRACT_WEEKDAY = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']


# ============================================================
# DASHBOARD PRINCIPAL
# ============================================================

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

    # ----- Período por defecto para los KPIs y el primer render de los
    # gráficos: últimos 30 días (hoy incluido) -----
    periodo_hasta = hoy.date()
    periodo_desde = periodo_hasta - timedelta(days=29)
    # modificado (Sedes): se estaba filtrando por sede_activa en las tarjetas
    # de arriba (stats) pero NO acá — los KPIs y los gráficos mostraban datos
    # de TODAS las sedes aunque el staff tuviera una sede fija o elegida.
    # Ahora usan el mismo sede_activa ya resuelto arriba.
    kpis = _calcular_kpis(periodo_desde, periodo_hasta, sede_activa)

    # ----- Datos iniciales de los gráficos (agrupados por día), para que la
    # página no se vea vacía antes de que cargue el JS. El usuario después
    # puede cambiar rango/agrupación y ahí entra en juego el AJAX. -----
    periodos_iniciales = generar_periodos(periodo_desde, periodo_hasta, 'dia')
    chart_ventas_labels, chart_ventas_valores = _serie_recaudacion(periodos_iniciales, sede_activa)
    _, chart_entradas_valores = _serie_entradas(periodos_iniciales, sede_activa)
    combos_iniciales = _combos_por_categoria(periodo_desde, periodo_hasta, sede_activa)

    # modificado (T6 - BI): gráfico nuevo #1, heatmap de entradas vendidas
    # por día de semana x hora de función, para el mismo período de 30 días
    # que ya usan los KPIs de arriba.
    heatmap = _heatmap_entradas_por_dia_hora(periodo_desde, periodo_hasta, sede_activa)

    # modificado (T6 - BI): gráfico nuevo #4, ranking comparativo entre
    # sedes — solo se calcula (y se muestra) para SuperUser.
    ranking_sedes = _ranking_sedes(periodo_desde, periodo_hasta) if request.user.is_superuser else None

    # modificado (T7 - BI): gráfico nuevo #1 (calificación vs. recaudación
    # por película) y #2 (ticket promedio con combo vs. sin combo), sobre
    # el mismo período de 30 días que ya usan los KPIs de arriba.
    rating_vs_recaudacion = _rating_vs_recaudacion(periodo_desde, periodo_hasta, sede_activa)
    atv_combo = _atv_combo_vs_sin_combo(periodo_desde, periodo_hasta, sede_activa)

    contexto = {
        'stats': stats,
        'kpis': kpis,
        'seccion_activa': 'inicio',
        'chart_ventas_labels': chart_ventas_labels,
        'chart_ventas_valores': chart_ventas_valores,
        'chart_entradas_valores': chart_entradas_valores,
        'chart_combos_labels': combos_iniciales['labels'],
        'chart_combos_valores': combos_iniciales['valores'],
        'periodo_desde_default': periodo_desde.strftime('%Y-%m-%d'),
        'periodo_hasta_default': periodo_hasta.strftime('%Y-%m-%d'),
        # modificado (T6 - BI)
        'heatmap_matriz': heatmap['matriz'],
        'heatmap_horas': heatmap['horas'],
        'ranking_sedes': ranking_sedes,
        # modificado (T7 - BI)
        'rating_recaudacion_datos': rating_vs_recaudacion,
        'atv_combo': atv_combo,
    }
    return render(request, 'panel/inicio.html', contexto)


# ============================================================
# nuevo: endpoints AJAX para los gráficos interactivos
# ============================================================

@staff_required
def dashboard_grafico_ventas(request):
    """
    GET ?desde=YYYY-MM-DD&hasta=YYYY-MM-DD&agrupacion=dia|semana|mes|
    bimestre|trimestre|cuatrimestre|anual&metrica=recaudacion|entradas

    Devuelve JSON {labels, valores, metrica, total} para redibujar el
    gráfico de ventas/entradas sin recargar la página. Lo consume
    static/js/panel/dashboard.js.
    """
    periodos, error = _parsear_periodos(request)
    if error:
        return JsonResponse({'error': error}, status=400)

    # modificado (Sedes): faltaba resolver y aplicar la sede activa acá —
    # el gráfico mostraba todas las sedes juntas aunque el staff tuviera
    # una sede fija o elegida en el selector del Panel.
    sede_activa = get_sede_activa_panel(request)

    metrica = request.GET.get('metrica', 'recaudacion')
    if metrica == 'entradas':
        labels, valores = _serie_entradas(periodos, sede_activa)
    elif metrica == 'recaudacion':
        labels, valores = _serie_recaudacion(periodos, sede_activa)
    else:
        return JsonResponse({'error': f"Métrica inválida: '{metrica}'."}, status=400)

    return JsonResponse({
        'labels': labels,
        'valores': valores,
        'metrica': metrica,
        'total': sum(valores),
    })


@staff_required
def dashboard_grafico_combos(request):
    """
    GET ?desde=YYYY-MM-DD&hasta=YYYY-MM-DD

    Devuelve JSON {labels, valores} con el consumo de comida (combos/
    bebidas/snacks/pochoclo) por categoría en el rango elegido. Usa el
    mismo selector de fechas que dashboard_grafico_ventas (sin agrupación,
    acá siempre se agrega todo el rango junto).
    """
    desde, hasta, error = _parsear_rango(request)
    if error:
        return JsonResponse({'error': error}, status=400)

    # modificado (Sedes): idem dashboard_grafico_ventas — faltaba filtrar
    # por sede activa.
    sede_activa = get_sede_activa_panel(request)
    return JsonResponse(_combos_por_categoria(desde, hasta, sede_activa))


@staff_required
def dashboard_kpis(request):
    """
    GET ?desde=YYYY-MM-DD&hasta=YYYY-MM-DD

    Devuelve JSON con los mismos KPIs que se calculan en inicio() para el
    período por defecto, pero recalculados para el rango que haya elegido
    el usuario en el selector de fechas del dashboard.
    """
    desde, hasta, error = _parsear_rango(request)
    if error:
        return JsonResponse({'error': error}, status=400)

    # modificado (Sedes): idem dashboard_grafico_ventas — faltaba filtrar
    # por sede activa.
    sede_activa = get_sede_activa_panel(request)
    return JsonResponse(_calcular_kpis(desde, hasta, sede_activa))


# ============================================================
# Helpers internos (no son vistas)
# ============================================================

def _parsear_rango(request):
    """Lee ?desde=&hasta= de la request y devuelve (desde, hasta, error)."""
    try:
        desde = date.fromisoformat(request.GET.get('desde', ''))
        hasta = date.fromisoformat(request.GET.get('hasta', ''))
    except ValueError:
        return None, None, 'Fechas inválidas. Formato esperado: YYYY-MM-DD.'
    if desde > hasta:
        return None, None, "La fecha 'desde' no puede ser posterior a 'hasta'."
    return desde, hasta, None


def _parsear_periodos(request):
    """Lee ?desde=&hasta=&agrupacion= y devuelve (periodos, error)."""
    desde, hasta, error = _parsear_rango(request)
    if error:
        return None, error
    agrupacion = request.GET.get('agrupacion', 'dia')
    try:
        periodos = generar_periodos(desde, hasta, agrupacion)
    except ValueError as e:
        return None, str(e)
    return periodos, None


def _serie_recaudacion(periodos, sede=None):
    """Recaudación (Pago.monto de pagos aprobados) por cada período.
    modificado (Sedes): filtro opcional por sede (vía reserva__funcion__sala__sede)."""
    labels = [p['etiqueta'] for p in periodos]
    filtro_sede = {'reserva__funcion__sala__sede': sede} if sede else {}
    valores = []
    for p in periodos:
        monto = Pago.objects.filter(
            estado='aprobado',
            fecha_pago__date__gte=p['inicio'],
            fecha_pago__date__lte=p['fin'],
            **filtro_sede,
        ).aggregate(t=Sum('monto'))['t'] or 0
        valores.append(float(monto))
    return labels, valores


def _serie_entradas(periodos, sede=None):
    """Entradas vendidas (Reserva.cantidad_entradas de reservas confirmadas,
    contadas por fecha de reserva) por cada período.
    modificado (Sedes): filtro opcional por sede (vía funcion__sala__sede)."""
    labels = [p['etiqueta'] for p in periodos]
    filtro_sede = {'funcion__sala__sede': sede} if sede else {}
    valores = []
    for p in periodos:
        entradas = Reserva.objects.filter(
            estado='confirmada',
            fecha_reserva__date__gte=p['inicio'],
            fecha_reserva__date__lte=p['fin'],
            **filtro_sede,
        ).aggregate(t=Sum('cantidad_entradas'))['t'] or 0
        valores.append(entradas)
    return labels, valores


def _combos_por_categoria(desde, hasta, sede=None):
    """Cantidad vendida de combos/bebidas/snacks/pochoclo (Combo.categoria)
    en pagos aprobados dentro del rango [desde, hasta].

    modificado: usa ItemPago (no Pago.combo/cantidad_combo). Esos dos
    campos de Pago son un resumen "legacy" que solo guarda el primer ítem
    de cada pedido (ver el comentario arriba de class ItemPago en
    pagos/models.py) — usarlos acá subcontaría los pedidos con más de un
    ítem. ItemPago es el detalle real, uno por cada ítem distinto del pedido.

    modificado (Sedes): filtro opcional por sede (vía
    pago__reserva__funcion__sala__sede — un salto más que en los otros
    helpers porque acá se parte de ItemPago, no de Pago/Reserva).
    """
    from pagos.models import ItemPago
    filtro_sede = {'pago__reserva__funcion__sala__sede': sede} if sede else {}
    datos = ItemPago.objects.filter(
        pago__estado='aprobado',
        pago__fecha_pago__date__gte=desde,
        pago__fecha_pago__date__lte=hasta,
        **filtro_sede,
    ).exclude(combo=None).values('combo__categoria').annotate(
        cantidad=Sum('cantidad')
    ).order_by('-cantidad')

    categoria_label = dict(Combo.CATEGORIA_CHOICES)
    labels = [categoria_label.get(d['combo__categoria'], d['combo__categoria']) for d in datos]
    valores = [d['cantidad'] for d in datos]
    return {'labels': labels, 'valores': valores}


def _calcular_kpis(desde, hasta, sede=None):
    """
    Calcula los KPIs de negocio para el rango [desde, hasta]:
      - recaudado_periodo, ticket_promedio
      - comparativa_pct: variación % de recaudación vs. el período
        inmediatamente anterior, de igual duración (None si no hay datos
        del período anterior para comparar)
      - top_peliculas: top 5 por recaudación (no por cantidad de funciones)
      - ocupacion_promedio: aproximación en base a
        (entradas pendientes+confirmadas) / capacidad de sala, promediada
        entre las funciones del período. Es una aproximación porque cuenta
        entradas reservadas, no asientos físicos puntuales (coincide con el
        criterio que ya usa Funcion.asientos_ocupados() en salas/models.py).
      - embudo: cantidad de reservas del período por estado
      - dia_top / horario_pico: día de la semana y horario con más
        reservas confirmadas en el período

    modificado (Sedes): parámetro `sede` opcional (Sede o None). Si viene,
    filtra pagos/reservas/funciones a esa sede antes de agregar. Antes esta
    función no sabía nada de sedes y siempre calculaba sobre TODAS.
    """
    dias_periodo = (hasta - desde).days + 1
    anterior_hasta = desde - timedelta(days=1)
    anterior_desde = anterior_hasta - timedelta(days=dias_periodo - 1)

    filtro_pago_sede = {'reserva__funcion__sala__sede': sede} if sede else {}
    filtro_funcion_sede = {'sala__sede': sede} if sede else {}
    filtro_reserva_sede = {'funcion__sala__sede': sede} if sede else {}

    pagos_periodo = Pago.objects.filter(
        estado='aprobado', fecha_pago__date__gte=desde, fecha_pago__date__lte=hasta,
        **filtro_pago_sede,
    )
    pagos_periodo_anterior = Pago.objects.filter(
        estado='aprobado', fecha_pago__date__gte=anterior_desde, fecha_pago__date__lte=anterior_hasta,
        **filtro_pago_sede,
    )

    recaudado_periodo = pagos_periodo.aggregate(t=Sum('monto'))['t'] or 0
    recaudado_periodo_anterior = pagos_periodo_anterior.aggregate(t=Sum('monto'))['t'] or 0
    ticket_promedio = pagos_periodo.aggregate(t=Avg('monto'))['t'] or 0

    if recaudado_periodo_anterior:
        comparativa_pct = round(
            (float(recaudado_periodo) - float(recaudado_periodo_anterior))
            / float(recaudado_periodo_anterior) * 100,
            1
        )
    else:
        comparativa_pct = None

    top_peliculas_qs = pagos_periodo.values(
        'reserva__funcion__pelicula__titulo'
    ).annotate(total=Sum('monto')).order_by('-total')[:5]
    top_peliculas = [
        {'titulo': t['reserva__funcion__pelicula__titulo'], 'total': float(t['total'])}
        for t in top_peliculas_qs
    ]

    # Ocupación promedio aproximada
    funciones_periodo = Funcion.objects.filter(
        fecha_hora__date__gte=desde, fecha_hora__date__lte=hasta,
        **filtro_funcion_sede,
    ).select_related('sala')
    ocupaciones = []
    for f in funciones_periodo:
        if not f.sala.capacidad:
            continue
        entradas = f.reservas.filter(
            estado__in=['pendiente', 'confirmada']
        ).aggregate(t=Sum('cantidad_entradas'))['t'] or 0
        ocupaciones.append(min(entradas / f.sala.capacidad, 1.0))
    ocupacion_promedio = round(sum(ocupaciones) / len(ocupaciones) * 100, 1) if ocupaciones else None

    # Embudo de reservas del período
    embudo_qs = Reserva.objects.filter(
        fecha_reserva__date__gte=desde, fecha_reserva__date__lte=hasta,
        **filtro_reserva_sede,
    ).values('estado').annotate(total=Count('id'))
    embudo = {e['estado']: e['total'] for e in embudo_qs}

    # Día de la semana + horario con más reservas confirmadas
    reservas_confirmadas = Reserva.objects.filter(
        estado='confirmada', fecha_reserva__date__gte=desde, fecha_reserva__date__lte=hasta,
        **filtro_reserva_sede,
    )
    dia_top_row = reservas_confirmadas.annotate(
        dow=ExtractWeekDay('funcion__fecha_hora')
    ).values('dow').annotate(total=Count('id')).order_by('-total').first()
    horario_pico_row = reservas_confirmadas.annotate(
        hora=ExtractHour('funcion__fecha_hora')
    ).values('hora').annotate(total=Count('id')).order_by('-total').first()

    dia_top = DIAS_EXTRACT_WEEKDAY[dia_top_row['dow'] - 1] if dia_top_row else None
    horario_pico = f"{horario_pico_row['hora']:02d}:00" if horario_pico_row else None

    return {
        'recaudado_periodo': float(recaudado_periodo),
        'ticket_promedio': float(ticket_promedio),
        'comparativa_pct': comparativa_pct,
        'top_peliculas': top_peliculas,
        'ocupacion_promedio': ocupacion_promedio,
        'embudo': embudo,
        'dia_top': dia_top,
        'horario_pico': horario_pico,
    }


# modificado (T6 - BI): dos helpers nuevos, no tocan ni reemplazan nada de
# lo que ya existía arriba.
# ============================================================
# nuevo (T6 - BI): heatmap día x hora + ranking de sedes
# ============================================================

def _heatmap_entradas_por_dia_hora(desde, hasta, sede=None):
    """
    Matriz de 7 (día de semana) x 24 (hora) con la cantidad de entradas
    vendidas (Reserva.cantidad_entradas, reservas confirmadas) para el
    rango [desde, hasta].

    modificado (T6 - BI): usa el mismo criterio que ya usa
    _calcular_kpis() para 'dia_top'/'horario_pico' — mismo filtro por
    fecha_reserva, mismas ExtractWeekDay/ExtractHour tomadas de
    funcion__fecha_hora (la franja horaria de la FUNCIÓN, no de cuándo se
    pagó) — pero acá arma la matriz completa de 7x24 en vez de quedarse
    solo con el máximo. Se usa cantidad de entradas y no recaudación
    porque Reserva no tiene monto propio (el monto vive en Pago, 1 a 1
    con la reserva) y este es el mismo dato base que ya usa el resto del
    dashboard para "horario pico"; ver T6_thomp.md, opción b.

    Devuelve {'matriz': [...], 'horas': [0..23]} donde 'matriz' es una
    lista de 7 filas (orden = DIAS_EXTRACT_WEEKDAY) y cada fila es
    {'dia': str, 'celdas': [{'valor': int, 'alpha': float 0-1}, ...24]}.
    'alpha' ya viene calculado (valor / máximo de toda la matriz) para
    poder pintar la celda directamente en el template sin lógica extra.
    """
    filtro_sede = {'funcion__sala__sede': sede} if sede else {}
    filas = Reserva.objects.filter(
        estado='confirmada',
        fecha_reserva__date__gte=desde,
        fecha_reserva__date__lte=hasta,
        **filtro_sede,
    ).annotate(
        dow=ExtractWeekDay('funcion__fecha_hora'),
        hora=ExtractHour('funcion__fecha_hora'),
    ).values('dow', 'hora').annotate(entradas=Sum('cantidad_entradas'))

    valores = [[0 for _ in range(24)] for _ in range(7)]
    for fila in filas:
        dia_idx = fila['dow'] - 1  # ExtractWeekDay: 1=Domingo..7=Sábado
        hora_idx = fila['hora']
        valores[dia_idx][hora_idx] = fila['entradas'] or 0

    maximo = max((v for fila in valores for v in fila), default=0)
    matriz = []
    for i, fila_valores in enumerate(valores):
        celdas = []
        for v in fila_valores:
            alpha = round(v / maximo, 2) if maximo else 0
            celdas.append({'valor': v, 'alpha': alpha})
        matriz.append({'dia': DIAS_EXTRACT_WEEKDAY[i], 'celdas': celdas})

    return {'matriz': matriz, 'horas': list(range(24))}


def _ranking_sedes(desde, hasta):
    """
    Comparativo entre todas las Sedes activas para el rango [desde,
    hasta]: recaudación total, ocupación promedio y ticket promedio (ATV).

    nuevo (T6 - BI): pensado para llamarse solo cuando
    request.user.is_superuser (ver inicio()) — un Staff con sede fija no
    debería ver comparativas de otras sedes. Reutiliza el mismo criterio
    de ocupación aproximada que ya usa _calcular_kpis() (entradas
    pendientes+confirmadas / capacidad de sala, promediada por función),
    pero separado por sede en vez de agregado global.
    """
    from sedes.models import Sede

    ranking = []
    for sede in Sede.objects.filter(activa=True).order_by('nombre'):
        pagos_sede = Pago.objects.filter(
            estado='aprobado',
            fecha_pago__date__gte=desde,
            fecha_pago__date__lte=hasta,
            reserva__funcion__sala__sede=sede,
        )
        recaudacion = pagos_sede.aggregate(t=Sum('monto'))['t'] or 0
        atv = pagos_sede.aggregate(t=Avg('monto'))['t'] or 0

        funciones_sede = Funcion.objects.filter(
            fecha_hora__date__gte=desde, fecha_hora__date__lte=hasta,
            sala__sede=sede,
        ).select_related('sala')
        ocupaciones = []
        for f in funciones_sede:
            if not f.sala.capacidad:
                continue
            entradas = f.reservas.filter(
                estado__in=['pendiente', 'confirmada']
            ).aggregate(t=Sum('cantidad_entradas'))['t'] or 0
            ocupaciones.append(min(entradas / f.sala.capacidad, 1.0))
        ocupacion_promedio = (
            round(sum(ocupaciones) / len(ocupaciones) * 100, 1) if ocupaciones else None
        )

        ranking.append({
            'sede': sede.nombre,
            'recaudacion': float(recaudacion),
            'atv': float(atv),
            'ocupacion_promedio': ocupacion_promedio,
            # modificado (T7 - Parte B): columna "cantidad de funciones" que
            # pedía SEDESactualizacion.txt punto 2 y esta tabla todavía no
            # tenía. Se reutiliza el mismo queryset funciones_sede ya armado
            # arriba para el cálculo de ocupación, no se agrega query nueva.
            'funciones_count': funciones_sede.count(),
        })

    ranking.sort(key=lambda r: r['recaudacion'], reverse=True)
    return ranking


# modificado (T7 - BI): dos helpers nuevos, no tocan ni reemplazan nada de
# lo que ya existía arriba (T6).
# ============================================================
# nuevo (T7 - BI): rating vs. recaudación + ATV con/sin combo
# ============================================================

def _rating_vs_recaudacion(desde, hasta, sede=None):
    """
    Por película: calificación promedio (RatingPelicula.puntuacion, vía el
    related_name 'ratings' de Pelicula — no requiere importar el modelo
    RatingPelicula acá, Django lo resuelve por relación inversa) vs.
    recaudación generada por esa película en el rango [desde, hasta]
    (Pago.monto de pagos aprobados, vía reserva__funcion__pelicula).

    nuevo (T7): decisión de interpretación — el RATING se promedia sobre
    TODO el historial de calificaciones de la película (no se filtra por
    [desde, hasta]), porque una calificación de un usuario no está atada a
    una compra puntual dentro del período, a diferencia de la recaudación
    que sí es "de ese período" igual que el resto de los KPIs del
    dashboard. Solo se incluyen películas que tengan AMBOS datos (al menos
    una calificación Y recaudación > 0 en el período) — si faltara
    cualquiera de los dos, el punto no aporta a la pregunta "¿correlaciona
    rating con ventas?" que pide la consigna.

    Devuelve una lista de dicts {titulo, rating_promedio, recaudacion},
    ordenada por recaudación descendente (mismo criterio que 'top_peliculas'
    de _calcular_kpis).
    """
    filtro_sede = {'reserva__funcion__sala__sede': sede} if sede else {}
    recaudacion_qs = Pago.objects.filter(
        estado='aprobado',
        fecha_pago__date__gte=desde, fecha_pago__date__lte=hasta,
        **filtro_sede,
    ).values('reserva__funcion__pelicula').annotate(recaudacion=Sum('monto'))
    recaudacion_por_pelicula = {
        r['reserva__funcion__pelicula']: float(r['recaudacion'] or 0) for r in recaudacion_qs
    }

    peliculas_con_rating = Pelicula.objects.filter(
        id__in=recaudacion_por_pelicula.keys()
    ).annotate(rating_promedio=Avg('ratings__puntuacion')).filter(
        rating_promedio__isnull=False
    ).values('id', 'titulo', 'rating_promedio')

    datos = [
        {
            'titulo': p['titulo'],
            'rating_promedio': round(p['rating_promedio'], 1),
            'recaudacion': recaudacion_por_pelicula.get(p['id'], 0),
        }
        for p in peliculas_con_rating
    ]
    datos.sort(key=lambda d: d['recaudacion'], reverse=True)
    return datos


def _atv_combo_vs_sin_combo(desde, hasta, sede=None):
    """
    Ticket promedio (ATV) comparado entre pagos que incluyeron al menos un
    ItemPago con combo asociado vs. pagos que no, para el rango [desde,
    hasta].

    nuevo (T7): mismo criterio de ATV que ya usa _calcular_kpis()
    (Avg('monto') sobre pagos aprobados) — no se inventa una fórmula
    nueva, solo se separa ese mismo cálculo en dos grupos según si el pago
    tiene o no items de combo (ItemPago, no el campo legacy Pago.combo —
    mismo motivo que ya documentó _combos_por_categoria: ese campo solo
    guarda el primer ítem del pedido).
    """
    from pagos.models import ItemPago  # import local, mismo patrón que _combos_por_categoria
    filtro_sede = {'reserva__funcion__sala__sede': sede} if sede else {}
    pagos_periodo = Pago.objects.filter(
        estado='aprobado',
        fecha_pago__date__gte=desde, fecha_pago__date__lte=hasta,
        **filtro_sede,
    )
    ids_con_combo = ItemPago.objects.filter(
        pago__in=pagos_periodo, combo__isnull=False
    ).values_list('pago_id', flat=True).distinct()

    pagos_con_combo = pagos_periodo.filter(id__in=ids_con_combo)
    pagos_sin_combo = pagos_periodo.exclude(id__in=ids_con_combo)

    return {
        'atv_con_combo': float(pagos_con_combo.aggregate(t=Avg('monto'))['t'] or 0),
        'atv_sin_combo': float(pagos_sin_combo.aggregate(t=Avg('monto'))['t'] or 0),
        'cantidad_con_combo': pagos_con_combo.count(),
        'cantidad_sin_combo': pagos_sin_combo.count(),
    }
