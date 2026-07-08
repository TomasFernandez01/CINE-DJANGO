from django.urls import path
from . import views

app_name = 'panel'

urlpatterns = [
    # Dashboard principal
    path('',                                    views.inicio,                   name='inicio'),
    # # ---- Películas ----
    path('peliculas/',                          views.peliculas_lista,          name='peliculas_lista'),
    path('peliculas/crear/',                    views.peliculas_crear,          name='peliculas_crear'),
    path('peliculas/<int:pelicula_id>/',        views.peliculas_detalle,        name='peliculas_detalle'),
    path('peliculas/<int:pelicula_id>/editar/', views.peliculas_editar,         name='peliculas_editar'),
    path('peliculas/tmdb/buscar/',              views.peliculas_buscar_tmdb,    name='peliculas_buscar_tmdb'),
    path('peliculas/tmdb/<int:tmdb_id>/',       views.peliculas_importar_tmdb,  name='peliculas_importar_tmdb'),
    # ---- Salas ----
    path('salas/',                              views.salas_lista,              name='salas_lista'),
    path('salas/crear/',                        views.salas_crear,              name='salas_crear'),
    path('salas/<int:sala_id>/editar/',         views.salas_editar,             name='salas_editar'),
    # ---- Funciones ----
    path('funciones/',                          views.funciones_lista,          name='funciones_lista'),
    path('funciones/crear/',                    views.funciones_crear,          name='funciones_crear'),
    path('funciones/<int:funcion_id>/',         views.funciones_detalle,        name='funciones_detalle'),
    path('funciones/<int:funcion_id>/editar/',  views.funciones_editar,         name='funciones_editar'),
    # ---- Reservas ----
    path('reservas/',                           views.reservas_lista,           name='reservas_lista'),
    path('reservas/<int:reserva_id>/',          views.reservas_detalle,         name='reservas_detalle'),
#   path('reservas/crear/',                     views.reservas_crear,           name='reservas_crear'),   # si lo agregás después
    path('reservas/<int:reserva_id>/editar/',   views.reservas_editar,          name='reservas_editar'),  # <-- ESTA
    # ---- Pagos ----
    path('pagos/',                              views.pagos_lista,              name='pagos_lista'),
    path('pagos/estadisticas/',                 views.pagos_estadisticas,       name='pagos_estadisticas'),
    # ---- Usuarios (solo superuser) ----
    path('usuarios/',                           views.usuarios_lista,           name='usuarios_lista'),
    path('usuarios/crear/',                     views.usuarios_crear,           name='usuarios_crear'),
    path('usuarios/<int:usuario_id>/',          views.usuarios_detalle,         name='usuarios_detalle'),
    path('usuarios/<int:usuario_id>/editar/',   views.usuarios_editar,          name='usuarios_editar'),
    # ---- Verificador QR (staff) ----
    path('verificador-qr/',                     views.verificador_qr,           name='verificador_qr'),

    # ---- Promociones: Combos ----
    path('combos/',                             views.combos_lista,  name='combos_lista'),
    path('combos/crear/',                       views.combos_crear,  name='combos_crear'),
    path('combos/<int:combo_id>/editar/',       views.combos_editar, name='combos_editar'),
    # ---- Promociones: Cupones ----
    path('cupones/',                            views.cupones_lista,  name='cupones_lista'),
    path('cupones/crear/',                      views.cupones_crear,  name='cupones_crear'),
    path('cupones/<int:cupon_id>/editar/',      views.cupones_editar, name='cupones_editar'),
    # ---- Promociones: Promo por Día ----
    path('promociones-dia/',                    views.promodia_lista,  name='promodia_lista'),
    path('promociones-dia/crear/',              views.promodia_crear,  name='promodia_crear'),
    path('promociones-dia/<int:promo_id>/editar/', views.promodia_editar, name='promodia_editar'),

    # ---- Cupones Usados (solo lectura) ----
    path('cupones-usados/',                     views.cupones_usados_lista, name='cupones_usados_lista'),
]