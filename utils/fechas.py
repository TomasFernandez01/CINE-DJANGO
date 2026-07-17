"""
utils/fechas.py

Helper compartido para el carrusel de fechas (usado por peliculas/views.py y salas/views.py).

Nota: se arman los nombres de dia "a mano" (DIAS_ABREV) en vez de usar
datetime.strftime('%a'), porque strftime depende del locale del sistema
operativo, no de LANGUAGE_CODE de Django. Con LANGUAGE_CODE = 'en-us' y sin
locale en español instalado en el server, strftime('%a') devolvía "Mon",
"Tue", etc. en vez de "Lun", "Mar".
"""
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
