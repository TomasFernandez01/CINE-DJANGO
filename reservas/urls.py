from django.urls import path
from . import views

app_name = 'reservas'

urlpatterns = [
    # Orginal
    path('reservar/<int:funcion_id>/', views.crear_reserva, name='crear_reserva'),
    # URL antigua - mantener para compatibilidad
    # cambiar a esta si falla path('crear/<int:funcion_id>/', views.crear_reserva, name='crear_reserva'),
    # URLs existentes
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
    # Original
    path('reserva/<int:reserva_id>/', views.detalle_reserva, name='detalle_reserva'),
    # cambiar a esta si falla path('detalle/<int:reserva_id>/', views.detalle_reserva, name='detalle_reserva'),
    path('cancelar/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),
    path('eliminar/<int:reserva_id>/', views.eliminar_reserva, name='eliminar_reserva'),

    # NUEVAS URLs para selección de asientos
    # NUEVAS URLs modificado: (función -> cantidad/promoción -> asientos -> combo -> pago) se agrego elegir entradas
    path('funcion/<int:funcion_id>/elegir-entrada/', views.elegir_tipo_entrada, name='elegir_tipo_entrada'),
    path('funcion/<int:funcion_id>/seleccionar-asientos/', views.seleccionar_asientos, name='seleccionar_asientos'),
    path('funcion/<int:funcion_id>/confirmar/', views.confirmar_reserva_con_asientos, name='confirmar_reserva_asientos'),
    path('funcion/<int:funcion_id>/verificar-asientos/', views.verificar_asientos_disponibles, name='verificar_asientos'),
]

