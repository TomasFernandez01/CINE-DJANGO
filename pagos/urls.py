from django.urls import path
from . import views

app_name = 'pagos'

urlpatterns = [
    path('pagar/<int:reserva_id>/', views.procesar_pago, name='procesar_pago'),
    path('comprobante/<int:pago_id>/', views.comprobante_pago, name='comprobante_pago'),
]