from django.urls import path
from . import views

app_name = 'pagos'

urlpatterns = [
    # modificado: nuevo paso 4 del flujo reordenado, antes de pagar
    # (función -> entrada -> asientos -> ESTE PASO: combo -> pago)
    path('combo/<int:reserva_id>/', views.elegir_combo, name='elegir_combo'),

    # URLs existentes
    path('procesar/<int:reserva_id>/', views.procesar_pago, name='procesar_pago'),
    path('comprobante/<int:pago_id>/', views.comprobante_pago, name='comprobante_pago'),
    
    # NUEVAS URLs para QR
    path('verificador/', views.verificador_qr, name='verificador_qr'),
    path('api/verificar-qr/', views.verificar_qr_api, name='verificar_qr_api'),
    path('api/marcar-escaneado/', views.marcar_qr_escaneado, name='marcar_qr_escaneado'),

    # Estadísticas staff
    path('estadisticas/', views.estadisticas_staff, name='estadisticas_staff'),
]
