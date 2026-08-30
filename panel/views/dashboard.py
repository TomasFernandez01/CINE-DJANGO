# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

# modificado (T14 - reorg Dashboard): este archivo era una sola vista
# inicio() con TODOS los gráficos de TODAS las apps mezclados en una sola
# página (~770 líneas de template). Se reparte en 4 sub-secciones —
# Catálogo / Promociones / Operaciones / Administración — cada una en su
# propia URL, más una vista de aterrizaje. Ningún cálculo cambia de
# fórmula: es 100% reubicación de dónde vive cada gráfico, no una reescritura
# de la lógica de negocio. Los 3 endpoints AJAX (dashboard_grafico_ventas,
# dashboard_grafico_combos, dashboard_kpis) tampoco cambian de URL/nombre —
# dashboard_grafico_combos ya no se usa desde ningún template (Consumo por
# categoría pasó a ser un render estático en Dashboard > Promociones, ver
# nota ahí abajo) pero se deja andando por compatibilidad, no molesta.
#
# Mapeo de gráficos (decidido con Tomás, ver conversación):
#   Catálogo:       Top 5 películas por recaudación, Calificación vs. recaudación
#   Promociones:    Consumo por categoría, Ticket con/sin combo, ROI de
#                   cupones, Cupones más usados, Cupones activos sin uso
#   Operaciones:    Stats del día + accesos rápidos, KPIs interactivos,
#                   Ventas del período (interactivo), Embudo de reservas,
#                   2 heatmaps, Método de pago más usado, Tiempo promedio
#                   hasta el pago
#   Administración: Ranking de sedes (SuperUser)
#
# Simplificación consciente: en el dashboard viejo, TODO se recalculaba en
# vivo por AJAX con un único selector de fechas (filtro-fechas + presets).
# Repartir eso en 4 páginas separadas manteniendo el mismo nivel de
# interactividad en las 4 hubiera significado cuadruplicar esa maquinaria
# de JS. Se deja la interactividad completa (AJAX + presets) SOLO en
# Operaciones, que es donde ya vivía el filtro principal. Catálogo,
# Promociones y Administración muestran los últimos 30 días fijos (mismo
# período que usaba el dashboard viejo por default) — Promociones y
# Operaciones sí conservan el filtro de fecha simple (GET, recarga de
# página) que ya existía para ROI de cupones / método de pago en
# pagos/estadisticas.html, ese no se perdió.

from datetime import date, timedelta
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from django.db.models.functions import ExtractHour, ExtractWeekDay
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from pagos.models import Pago
from peliculas.models import Pelicula
from promociones.models import Combo, Cupon, CuponUsado
from reservas.models import Reserva
from salas.models import Funcion
from utils.fechas import generar_periodos
from ..decorators import staff_required, get_sede_activa_panel
# modificado (T14): se reusan estos 4 helpers de pagos.py en vez de
# duplicarlos acá — son módulos hermanos dentro de panel/views/, sin
# import circular (pagos.py no importa nada de dashboard.py).
from .pagos import (
    _parsear_rango_pagos,
    _roi_cupones,
    _distribucion_metodo_pago,
    _tiempo_promedio_hasta_pago,
)

# ExtractWeekDay de Django: 1=Domingo, 2=Lunes, ..., 7=Sábado (¡ojo! no es
# igual a date.weekday(), que arranca en Lunes=0).
DIAS_EXTRACT_WEEKDAY = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']


# ============================================================
# nuevo (T14): ATERRIZAJE DE DASHBOARD — menú de 4 tarjetas
# ============================================================

@staff_required
def inicio(request):
    """
    modificado (T14): esto ANTES era la página con todos los gráficos.
    Ahora es solo un menú de 4 tarjetas grandes a las sub-secciones. Se
    mantiene el nombre de URL 'panel:inicio' (y la ruta '') sin cambios:
    hay ~10 templates en todo Panel que linkean acá como "volver al
    inicio" (botón INICIO en salas/sedes/películas/etc.) y el breadcrumb
    de base_panel.html también apunta acá — cambiar el nombre de URL
    hubiera significado tocar todos esos templates sin necesidad.
    """
    return render(request, 'panel/dashboard/inicio.html', {'seccion_activa': 'dashboard'})


@staff_required
def dashboard_catalogo(request):
    """nuevo (T14): Top 5 películas por recaudación + Calificación vs.
    recaudación. Últimos 30 días fijos (sin selector interactivo, ver nota
    de simplificación arriba del archivo)."""
    sede_activa = get_sede_activa_panel(request)
    hasta = timezone.now().date()
    desde = hasta - timedelta(days=29)

    # nuevo (T14): "Películas en cartelera" vivía en el stat-grid de la
    # vieja inicio() (mezclado con recaudación/QR/reservas, que son de
    # Operaciones). Es un dato de Catálogo, así que se muda para acá.
    stats = {
        'peliculas_cartelera': Pelicula.objects.filter(en_cartelera=True).count(),
        'peliculas_total': Pelicula.objects.count(),
    }

    contexto = {
        'seccion_activa': 'dashboard',
        'periodo_desde': desde,
        'periodo_hasta': hasta,
        'stats': stats,
        'top_peliculas': _top_peliculas_por_recaudacion(desde, hasta, sede_activa),
        'rating_recaudacion_datos': _rating_vs_recaudacion(desde, hasta, sede_activa),
    }
    return render(request, 'panel/dashboard/catalogo.html', contexto)


@staff_required
def dashboard_promociones(request):
    """nuevo (T14): Consumo por categoría, Ticket con/sin combo y ROI de
    cupones comparten un filtro de fecha simple (GET, mismo patrón que ya
    usaba pagos/estadisticas.html para esto). Cupones más usados / activos
    sin uso mantienen su lógica original de ventanas fijas (hoy/semana/mes),
    independiente del filtro de arriba — así funcionaban en
    cupones/estadisticas.html, no se les cambió el criterio."""
    sede_activa = get_sede_activa_panel(request)
    desde, hasta, error_rango = _parsear_rango_pagos(request)
    if error_rango:
        hasta = timezone.now().date()
        desde = hasta - timedelta(days=29)

    combos = _combos_por_categoria(desde, hasta, sede_activa)
    atv_combo = _atv_combo_vs_sin_combo(desde, hasta, sede_activa)
    roi_cupones = _roi_cupones(desde, hasta, sede_activa)
    cupones_stats = _cupones_stats_ventanas()

    contexto = {
        'seccion_activa': 'dashboard',
        'rango_desde': desde.strftime('%Y-%m-%d'),
        'rango_hasta': hasta.strftime('%Y-%m-%d'),
        'rango_error': error_rango,
        'chart_combos_labels': combos['labels'],
        'chart_combos_valores': combos['valores'],
        'atv_combo': atv_combo,
        'roi_cupones': roi_cupones,
        'cupones_stats': cupones_stats['stats'],
        'top_cupones': cupones_stats['top_cupones'],
        'cupones_activos_sin_uso': cupones_stats['cupones_activos_sin_uso'],
    }
    return render(request, 'panel/dashboard/promociones.html', contexto)


@staff_required
def dashboard_operaciones(request):
    """modificado (T14): esto es lo que antes era inicio() completo, menos
    Top 5 películas / Calificación vs. recaudación (-> Catálogo) y menos
    Consumo por categoría (-> Promociones). Se le suman Método de pago más
    usado y Tiempo promedio hasta el pago, que vivían en
    pagos/estadisticas.html. Mantiene el filtro interactivo (AJAX +
    presets) para KPIs/Ventas/Embudo/Heatmaps — Método de pago usa su
    propio filtro simple aparte (mismo que tenía en pagos/estadisticas.html)."""
    ahora = timezone.now()
    hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    semana = hoy - timedelta(days=7)

    sede_activa = get_sede_activa_panel(request)
    filtro_funcion = {'sala__sede': sede_activa} if sede_activa else {}
    filtro_reserva = {'funcion__sala__sede': sede_activa} if sede_activa else {}
    filtro_pago = {'reserva__funcion__sala__sede': sede_activa} if sede_activa else {}

    stats = {
        'funciones_hoy': Funcion.objects.filter(
            fecha_hora__gte=hoy, fecha_hora__lt=hoy + timedelta(days=1),
            disponible=True, **filtro_funcion
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

    periodo_hasta = hoy.date()
    periodo_desde = periodo_hasta - timedelta(days=29)
    kpis = _calcular_kpis(periodo_desde, periodo_hasta, sede_activa)

    periodos_iniciales = generar_periodos(periodo_desde, periodo_hasta, 'dia')
    chart_ventas_labels, chart_ventas_valores = _serie_recaudacion(periodos_iniciales, sede_activa)
    _, chart_entradas_valores = _serie_entradas(periodos_iniciales, sede_activa)

    heatmap = _heatmap_entradas_por_dia_hora(periodo_desde, periodo_hasta, sede_activa)
    heatmap_recaudacion = _heatmap_recaudacion_por_dia_hora(periodo_desde, periodo_hasta, sede_activa)

    # nuevo (T14): Método de pago + tiempo hasta el pago, mudados desde
    # pagos/estadisticas.html. Filtro de fecha propio (GET simple), no
    # comparte el filtro interactivo de KPIs/Ventas de arriba — así
    # funcionaban antes, en pagos/estadisticas.html, no se les cambió el
    # criterio al mudarlos.
    desde_mp, hasta_mp, error_rango_mp = _parsear_rango_pagos(request)
    if error_rango_mp:
        hasta_mp = periodo_hasta
        desde_mp = periodo_desde
    metodo_pago = _distribucion_metodo_pago(desde_mp, hasta_mp, sede_activa)
    tiempo_hasta_pago = _tiempo_promedio_hasta_pago(sede_activa)

    contexto = {
        'seccion_activa': 'dashboard',
        'stats': stats,
        'kpis': kpis,
        'chart_ventas_labels': chart_ventas_labels,
        'chart_ventas_valores': chart_ventas_valores,
        'chart_entradas_valores': chart_entradas_valores,
        'periodo_desde_default': periodo_desde.strftime('%Y-%m-%d'),
        'periodo_hasta_default': periodo_hasta.strftime('%Y-%m-%d'),
        'heatmap_matriz': heatmap['matriz'],
        'heatmap_horas': heatmap['horas'],
        'heatmap_recaudacion_matriz': heatmap_recaudacion['matriz'],
        'metodo_pago_labels': metodo_pago['labels'],
        'metodo_pago_valores': metodo_pago['valores'],
        'tiempo_hasta_pago': tiempo_hasta_pago,
        'rango_mp_desde': desde_mp.strftime('%Y-%m-%d'),
        'rango_mp_hasta': hasta_mp.strftime('%Y-%m-%d'),
        'rango_mp_error': error_rango_mp,
    }
    return render(request, 'panel/dashboard/operaciones.html', contexto)


@staff_required
def dashboard_administracion(request):
    """modificado (T14): Ranking de sedes, mudado tal cual desde
    inicio(). Sigue siendo exclusivo de SuperUser — si un Staff entra acá
    por URL directa, se lo redirige al aterrizaje de Dashboard con un
    aviso, en vez de mostrarle una página vacía."""
    if not request.user.is_superuser:
        messages.error(request, 'Esta sección es exclusiva de SuperUser.')
        return redirect('panel:inicio')

    hasta = timezone.now().date()
    desde = hasta - timedelta(days=29)
    contexto = {
        'seccion_activa': 'dashboard',
        'periodo_desde': desde,
        'periodo_hasta': hasta,
        'ranking_sedes': _ranking_sedes(desde, hasta),
    }
    return render(request, 'panel/dashboard/administracion.html', contexto)


# ============================================================
# endpoints AJAX del dashboard interactivo (solo Operaciones)
# ============================================================

@staff_required
def dashboard_grafico_ventas(request):
    """
    GET ?desde=YYYY-MM-DD&hasta=YYYY-MM-DD&agrupacion=dia|semana|mes|
    bimestre|trimestre|cuatrimestre|anual&metrica=recaudacion|entradas

    Devuelve JSON {labels, valores, metrica, total} para redibujar el
    gráfico de ventas/entradas sin recargar la página. Lo consume
    static/js/panel/dashboard_operaciones.js (Dashboard > Operaciones).
    """
    periodos, error = _parsear_periodos(request)
    if error:
        return JsonResponse({'error': error}, status=400)

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

    modificado (T14): ya no se consume desde ningún template — "Consumo
    por categoría" pasó a renderizarse una sola vez server-side en
    Dashboard > Promociones (con su propio filtro GET, no AJAX). Se deja
    este endpoint vivo por si algo externo lo llamaba y por compatibilidad
    con integraciones, no molesta que quede.
    """
    desde, hasta, error = _parsear_rango(request)
    if error:
        return JsonResponse({'error': error}, status=400)

    sede_activa = get_sede_activa_panel(request)
    return JsonResponse(_combos_por_categoria(desde, hasta, sede_activa))


@staff_required
def dashboard_kpis(request):
    """
    GET ?desde=YYYY-MM-DD&hasta=YYYY-MM-DD

    Devuelve JSON con los KPIs de Dashboard > Operaciones para el rango
    que haya elegido el usuario en el selector de fechas.
    """
    desde, hasta, error = _parsear_rango(request)
    if error:
        return JsonResponse({'error': error}, status=400)

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

    modificado (T14 - bug categoría libre): 'categoria' del modelo Combo
    ya no tiene 'choices' (ver promociones/models.py) — sigue siendo texto
    libre, así que categoria_label.get(clave, clave) ya cubría bien el caso
    de una categoría nueva sin traducción (fallback al valor crudo), no
    hizo falta tocar nada acá por ese cambio.
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


def _top_peliculas_por_recaudacion(desde, hasta, sede=None):
    """nuevo (T14): extraído de _calcular_kpis() (antes vivía adentro,
    mezclado con KPIs financieros/operativos que no le corresponden a
    Catálogo). Misma fórmula exacta que tenía ahí, sin cambios — top 5 por
    recaudación (Pago.monto), no por cantidad de funciones."""
    filtro_sede = {'reserva__funcion__sala__sede': sede} if sede else {}
    top_qs = Pago.objects.filter(
        estado='aprobado', fecha_pago__date__gte=desde, fecha_pago__date__lte=hasta,
        **filtro_sede,
    ).values('reserva__funcion__pelicula__titulo').annotate(total=Sum('monto')).order_by('-total')[:5]
    return [
        {'titulo': t['reserva__funcion__pelicula__titulo'], 'total': float(t['total'])}
        for t in top_qs
    ]


def _cupones_stats_ventanas():
    """nuevo (T14): mudado tal cual desde promociones.py::cupones_estadisticas
    (ese view se retiró, todo su contenido de análisis vive acá ahora).
    Mismas ventanas fijas (hoy/semana/mes/total) que tenía, sin cambios de
    fórmula. Nota: al igual que en el original, esto NO filtra por sede —
    así funcionaba antes (posible punto a revisar en una tanda futura, no
    se tocó acá para no cambiar comportamiento sin que se pida)."""
    ahora = timezone.now()
    hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    semana = hoy - timedelta(days=7)
    mes = hoy - timedelta(days=30)

    usos_hoy = CuponUsado.objects.filter(fecha_uso__gte=hoy)
    usos_semana = CuponUsado.objects.filter(fecha_uso__gte=semana)
    usos_mes = CuponUsado.objects.filter(fecha_uso__gte=mes)

    stats = {
        'usos_hoy': usos_hoy.count(),
        'usos_semana': usos_semana.count(),
        'usos_mes': usos_mes.count(),
        'usos_total': CuponUsado.objects.count(),
        'descuento_hoy': usos_hoy.aggregate(t=Sum('descuento_aplicado'))['t'] or 0,
        'descuento_semana': usos_semana.aggregate(t=Sum('descuento_aplicado'))['t'] or 0,
        'descuento_mes': usos_mes.aggregate(t=Sum('descuento_aplicado'))['t'] or 0,
        'descuento_total': CuponUsado.objects.aggregate(t=Sum('descuento_aplicado'))['t'] or 0,
    }

    top_cupones = CuponUsado.objects.values(
        'cupon__codigo', 'cupon__descripcion'
    ).annotate(
        veces_usado=Count('id'),
        descuento_generado=Sum('descuento_aplicado')
    ).order_by('-veces_usado')[:10]

    cupones_activos_sin_uso = Cupon.objects.filter(
        activo=True
    ).exclude(
        id__in=usos_mes.values_list('cupon_id', flat=True)
    ).order_by('-fecha_inicio')[:10]

    return {
        'stats': stats,
        'top_cupones': top_cupones,
        'cupones_activos_sin_uso': cupones_activos_sin_uso,
    }


def _calcular_kpis(desde, hasta, sede=None):
    """
    Calcula los KPIs de negocio para el rango [desde, hasta]:
      - recaudado_periodo, ticket_promedio
      - comparativa_pct: variación % de recaudación vs. el período
        inmediatamente anterior, de igual duración (None si no hay datos
        del período anterior para comparar)
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

    modificado (T14 - reorg Dashboard): 'top_peliculas' se sacó de acá y
    pasó a su propia función _top_peliculas_por_recaudacion() — pertenece
    conceptualmente a Catálogo, no a estos KPIs operativos/financieros.
    Se actualizó también dashboard_operaciones.js para que ya no espere
    ese campo en la respuesta de dashboard_kpis.
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
        'ocupacion_promedio': ocupacion_promedio,
        'embudo': embudo,
        'dia_top': dia_top,
        'horario_pico': horario_pico,
    }


# ============================================================
# nuevo (T6 - BI): heatmap día x hora + ranking de sedes
# ============================================================

def _heatmap_entradas_por_dia_hora(desde, hasta, sede=None):
    """
    Matriz 7 (día de semana) x 24 (hora) de cantidad de entradas vendidas
    (Reserva.cantidad_entradas, reservas confirmadas), agrupadas por el
    día/hora de la FUNCIÓN (no de la reserva) — responde "¿qué franjas
    horarias son las más elegidas?", que es sobre cuándo va la gente al
    cine, no cuándo compra el ticket.
    """
    filtro_sede = {'funcion__sala__sede': sede} if sede else {}
    filas = Reserva.objects.filter(
        estado='confirmada',
        funcion__fecha_hora__date__gte=desde,
        funcion__fecha_hora__date__lte=hasta,
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


def _heatmap_recaudacion_por_dia_hora(desde, hasta, sede=None):
    """
    nuevo (T11): misma matriz 7x24 que _heatmap_entradas_por_dia_hora, pero
    con recaudación (Pago.monto de pagos 'aprobado') en vez de cantidad de
    entradas. Se pidió explícitamente tener los DOS heatmaps, no reemplazar
    el existente.

    El eje día/hora sigue siendo el de la FUNCIÓN (reserva__funcion__fecha_hora),
    igual que el heatmap de entradas, para que ambos sean comparables celda a
    celda. El filtro de período es por fecha_pago (mismo criterio que
    _ranking_sedes usa para "recaudación del período").
    """
    filtro_sede = {'reserva__funcion__sala__sede': sede} if sede else {}
    filas = Pago.objects.filter(
        estado='aprobado',
        fecha_pago__date__gte=desde,
        fecha_pago__date__lte=hasta,
        **filtro_sede,
    ).annotate(
        dow=ExtractWeekDay('reserva__funcion__fecha_hora'),
        hora=ExtractHour('reserva__funcion__fecha_hora'),
    ).values('dow', 'hora').annotate(recaudacion=Sum('monto'))

    valores = [[0 for _ in range(24)] for _ in range(7)]
    for fila in filas:
        dia_idx = fila['dow'] - 1  # ExtractWeekDay: 1=Domingo..7=Sábado
        hora_idx = fila['hora']
        valores[dia_idx][hora_idx] = float(fila['recaudacion'] or 0)

    maximo = max((v for fila in valores for v in fila), default=0)
    matriz = []
    for i, fila_valores in enumerate(valores):
        celdas = []
        for v in fila_valores:
            alpha = round(v / maximo, 2) if maximo else 0
            celdas.append({'valor': round(v, 2), 'alpha': alpha})
        matriz.append({'dia': DIAS_EXTRACT_WEEKDAY[i], 'celdas': celdas})

    return {'matriz': matriz, 'horas': list(range(24))}


def _ranking_sedes(desde, hasta):
    """
    Comparativo entre todas las Sedes activas para el rango [desde,
    hasta]: recaudación total, ocupación promedio y ticket promedio (ATV).

    nuevo (T6 - BI): pensado para llamarse solo cuando
    request.user.is_superuser (ver dashboard_administracion()) — un Staff
    con sede fija no debería ver comparativas de otras sedes. Reutiliza el
    mismo criterio de ocupación aproximada que ya usa _calcular_kpis()
    (entradas pendientes+confirmadas / capacidad de sala, promediada por
    función), pero separado por sede en vez de agregado global.
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
            'funciones_count': funciones_sede.count(),
        })

    ranking.sort(key=lambda r: r['recaudacion'], reverse=True)
    return ranking


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
    que sí es "de ese período". Solo se incluyen películas que tengan
    AMBOS datos (al menos una calificación Y recaudación > 0 en el
    período).

    Devuelve una lista de dicts {titulo, rating_promedio, recaudacion},
    ordenada por recaudación descendente.
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
    tiene o no items de combo (ItemPago, no el campo legacy Pago.combo).
    """
    from pagos.models import ItemPago
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
