from django.urls import path
from . import views

app_name = 'reservas'

urlpatterns = [
    # modificado: se borró la ruta vieja 'reservar/<int:funcion_id>/' -> crear_reserva.
    # Esa vista solo hacía un redirect a seleccionar_asientos y no la usaba ni un solo
    # link/template de todo el proyecto (se confirmó buscando en todas las apps, incluidas
    # Pagos y Panel). Junto con la ruta se borró la vista, el template y su CSS/JS.
    path('mis-reservas/', views.mis_reservas, name='mis_reservas'),
    path('reserva/<int:reserva_id>/', views.detalle_reserva, name='detalle_reserva'),
    path('cancelar/<int:reserva_id>/', views.cancelar_reserva, name='cancelar_reserva'),
    path('eliminar/<int:reserva_id>/', views.eliminar_reserva, name='eliminar_reserva'),

    # Flujo de compra: función -> cantidad/promoción -> asientos -> combo -> pago
    path('funcion/<int:funcion_id>/elegir-entrada/', views.elegir_tipo_entrada, name='elegir_tipo_entrada'),
    path('funcion/<int:funcion_id>/seleccionar-asientos/', views.seleccionar_asientos, name='seleccionar_asientos'),
    path('funcion/<int:funcion_id>/confirmar/', views.confirmar_reserva_con_asientos, name='confirmar_reserva_asientos'),
    path('funcion/<int:funcion_id>/verificar-asientos/', views.verificar_asientos_disponibles, name='verificar_asientos'),
]

