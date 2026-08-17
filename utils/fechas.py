"""
utils/fechas.py

Helper compartido para el carrusel de fechas (usado por peliculas/views.py y salas/views.py).

Nota: se arman los nombres de dia "a mano" (DIAS_ABREV) en vez de usar
datetime.strftime('%a'), porque strftime depende del locale del sistema
operativo, no de LANGUAGE_CODE de Django. Con LANGUAGE_CODE = 'en-us' y sin
locale en español instalado en el server, strftime('%a') devolvía "Mon",
"Tue", etc. en vez de "Lun", "Mar".
"""
from datetime import timedelta  # modificado: hace falta timedelta "pelado" para generar_periodos()
from django.utils import timezone

DIAS_ABREV = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']  # date.weekday(): Lunes = 0


def generar_proximos_dias(cantidad=20):
    """Devuelve una lista de dicts para el carrusel de fechas:
    [{'valor': 'YYYY-MM-DD', 'dia_semana': 'Hoy'/'Lun'/..., 'dia_mes': 'DD/MM'}, ...]
    """
    hoy = timezone.now().date()
    dias = []
    for i in range(cantidad):
        dia = hoy + timezone.timedelta(days=i)
        dias.append({
            'valor': dia.strftime('%Y-%m-%d'),
            'dia_semana': 'Hoy' if i == 0 else DIAS_ABREV[dia.weekday()],
            'dia_mes': dia.strftime('%d/%m'),
        })
    return dias


def formatear_fecha(fecha_obj):
    """nuevo: da formato a UNA fecha puntual (a diferencia de generar_proximos_dias,
    que arma un rango consecutivo). Se usa en detalle_pelicula, donde el carrusel
    solo debe mostrar los dias en los que esa pelicula realmente tiene funcion."""
    hoy = timezone.now().date()
    return {
        'valor': fecha_obj.strftime('%Y-%m-%d'),
        'dia_semana': 'Hoy' if fecha_obj == hoy else DIAS_ABREV[fecha_obj.weekday()],
        'dia_mes': fecha_obj.strftime('%d/%m'),
    }


# ============================================================
# nuevo: agrupación de rangos de fechas en "períodos" (día, semana, mes,
# bimestre, trimestre, cuatrimestre, año), para los gráficos interactivos
# del dashboard (panel/views/dashboard.py). Se resuelve todo con la lib
# estándar (calendar/date/timedelta) a propósito, para no sumar una
# dependencia nueva (python-dateutil) que no está confirmada en el server.
# ============================================================

AGRUPACIONES_VALIDAS = ['dia', 'semana', 'mes', 'bimestre', 'trimestre', 'cuatrimestre', 'anual']
MESES_ABREV = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

_DIAS_POR_AGRUPACION = {'dia': 1, 'semana': 7}
_MESES_POR_AGRUPACION = {'mes': 1, 'bimestre': 2, 'trimestre': 3, 'cuatrimestre': 4, 'anual': 12}


def sumar_meses(fecha_obj, cantidad):
    """Suma `cantidad` meses a una date, ajustando el día si el mes destino
    tiene menos días (ej: 31/01 + 1 mes -> 28/02 o 29/02 según bisiesto)."""
    import calendar
    mes_total = fecha_obj.month - 1 + cantidad
    anio = fecha_obj.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = min(fecha_obj.day, calendar.monthrange(anio, mes)[1])
    return fecha_obj.replace(year=anio, month=mes, day=dia)


def generar_periodos(desde, hasta, agrupacion, tope=60):
    """
    Parte el rango [desde, hasta] (objetos date, ambos incluidos) en
    "períodos" según `agrupacion`, para agregar recaudación/entradas por
    período en los gráficos del dashboard.

    Devuelve una lista de dicts: [{'inicio': date, 'fin': date, 'etiqueta': str}, ...]

    Lanza ValueError (mensaje ya en español, pensado para devolverse tal
    cual en un JsonResponse de error) si:
      - la agrupación no es una de AGRUPACIONES_VALIDAS
      - 'desde' es posterior a 'hasta'
      - el rango genera más de `tope` períodos (ej: agrupar por "día" un
        rango de 5 años) — evita respuestas gigantes/gráficos ilegibles.
    """
    if agrupacion not in AGRUPACIONES_VALIDAS:
        raise ValueError(f"Agrupación inválida: '{agrupacion}'.")
    if desde > hasta:
        raise ValueError("La fecha 'desde' no puede ser posterior a 'hasta'.")

    periodos = []
    actual = desde
    while actual <= hasta:
        if agrupacion in _DIAS_POR_AGRUPACION:
            fin_periodo = min(actual + timedelta(days=_DIAS_POR_AGRUPACION[agrupacion] - 1), hasta)
        else:
            fin_periodo = min(
                sumar_meses(actual, _MESES_POR_AGRUPACION[agrupacion]) - timedelta(days=1),
                hasta
            )

        periodos.append({
            'inicio': actual,
            'fin': fin_periodo,
            'etiqueta': _etiqueta_periodo(actual, fin_periodo, agrupacion),
        })

        if len(periodos) > tope:
            raise ValueError(
                f"Ese rango de fechas genera demasiados períodos agrupando por "
                f"'{agrupacion}' (más de {tope}). Elegí un rango más corto o una "
                f"agrupación más amplia."
            )

        actual = fin_periodo + timedelta(days=1)

    return periodos


def _etiqueta_periodo(inicio, fin, agrupacion):
    """Texto corto para el eje X del gráfico, según la agrupación elegida."""
    if agrupacion == 'dia':
        return inicio.strftime('%d/%m')
    if agrupacion == 'semana':
        return f"{inicio.strftime('%d/%m')}-{fin.strftime('%d/%m')}"
    if agrupacion == 'mes':
        return f"{MESES_ABREV[inicio.month - 1]} {inicio.year}"
    if agrupacion == 'anual':
        return str(inicio.year)
    # bimestre / trimestre / cuatrimestre: rango de meses abreviados
    if inicio.year == fin.year:
        return f"{MESES_ABREV[inicio.month - 1]}-{MESES_ABREV[fin.month - 1]} {inicio.year}"
    return f"{MESES_ABREV[inicio.month - 1]} {inicio.year}-{MESES_ABREV[fin.month - 1]} {fin.year}"
