from django.urls import path
from . import views

app_name = 'pagos'

urlpatterns = [
    path('combo/<int:reserva_id>/', views.elegir_combo, name='elegir_combo'),
    path('procesar/<int:reserva_id>/', views.procesar_pago, name='procesar_pago'),
    path('comprobante/<int:pago_id>/', views.comprobante_pago, name='comprobante_pago'),
    path('api/verificar-qr/', views.verificar_qr_api, name='verificar_qr_api'),
    path('api/marcar-escaneado/', views.marcar_qr_escaneado, name='marcar_qr_escaneado'),
]
