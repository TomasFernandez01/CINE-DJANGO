from django.urls import path
from . import views

app_name = 'panel'

urlpatterns = [
    # Dashboard principal
    path('', views.inicio, name='inicio'),

    # ---- Películas ----
    path('peliculas/', views.peliculas_lista, name='peliculas_lista'),
    path('peliculas/<int:pelicula_id>/', views.peliculas_detalle, name='peliculas_detalle'),

    # ---- Salas y Funciones ----
    path('salas/', views.salas_lista, name='salas_lista'),
    path('funciones/', views.funciones_lista, name='funciones_lista'),
    path('funciones/<int:funcion_id>/', views.funciones_detalle, name='funciones_detalle'),

    # ---- Reservas ----
    path('reservas/', views.reservas_lista, name='reservas_lista'),
    path('reservas/<int:reserva_id>/', views.reservas_detalle, name='reservas_detalle'),

    # ---- Pagos ----
    path('pagos/', views.pagos_lista, name='pagos_lista'),
    path('pagos/estadisticas/', views.pagos_estadisticas, name='pagos_estadisticas'),

    # ---- Usuarios (solo superuser) ----
    path('usuarios/', views.usuarios_lista, name='usuarios_lista'),
    path('usuarios/<int:usuario_id>/', views.usuarios_detalle, name='usuarios_detalle'),

    # ---- Verificador QR (staff) ----
    path('verificador-qr/', views.verificador_qr, name='verificador_qr'),
]