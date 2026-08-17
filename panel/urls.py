from django.urls import path
from . import views

app_name = 'panel'

urlpatterns = [
    # Dashboard 
    path('',                                    views.inicio,                   name='inicio'),
    # modificado: endpoints AJAX del dashboard interactivo (ver panel/views/dashboard.py)
    path('dashboard/grafico-ventas/',            views.dashboard_grafico_ventas, name='dashboard_grafico_ventas'),
    path('dashboard/grafico-combos/',            views.dashboard_grafico_combos, name='dashboard_grafico_combos'),
    path('dashboard/kpis/',                      views.dashboard_kpis,           name='dashboard_kpis'),
    # ---- Películas ----------------------------------------------------------------------------
    path('peliculas/',                          views.peliculas_lista,          name='peliculas_lista'),
    # CRUD
    path('peliculas/crear/',                    views.peliculas_crear,          name='peliculas_crear'),
    path('peliculas/<int:pelicula_id>/',        views.peliculas_detalle,        name='peliculas_detalle'),
    path('peliculas/<int:pelicula_id>/editar/', views.peliculas_editar,         name='peliculas_editar'),
    path('peliculas/eliminar/',                 views.peliculas_eliminar,       name='peliculas_eliminar'),
    # API
    path('peliculas/tmdb/buscar/',              views.peliculas_buscar_tmdb,    name='peliculas_buscar_tmdb'),
    path('peliculas/tmdb/<int:tmdb_id>/',       views.peliculas_importar_tmdb,  name='peliculas_importar_tmdb'),
    # ---- Salas ------------------------------------------------------------------------------------
    path('salas/',                              views.salas_lista,              name='salas_lista'),
    # CRUD
    path('salas/crear/',                        views.salas_crear,              name='salas_crear'),
    path('salas/<int:sala_id>/editar/',         views.salas_editar,             name='salas_editar'),
    path('salas/eliminar/',                     views.salas_eliminar,            name='salas_eliminar'),
    # mapa-salas
    path('salas/<int:sala_id>/asientos/',       views.salas_asientos,            name='salas_asientos'),
    path('salas/<int:sala_id>/asientos/bloquear/',views.salas_asientos_bloquear,   name='salas_asientos_bloquear'),
    path('salas/<int:sala_id>/asientos/desbloquear/',views.salas_asientos_desbloquear, name='salas_asientos_desbloquear'),
    path('salas/<int:sala_id>/asientos/categoria/asignar/', views.salas_categoria_asignar, name='salas_categoria_asignar'),
    path('salas/<int:sala_id>/asientos/categoria/quitar/',  views.salas_categoria_quitar,  name='salas_categoria_quitar'),
    # ---- Funciones --------------------------------------------------------------------------------
    path('funciones/',                          views.funciones_lista,          name='funciones_lista'),
    # MODIFICACION GEMINI: endpoint para verificar margen de tiempo entre funciones
    path('funciones/margen-tiempo/',            views.funciones_margen_tiempo,  name='funciones_margen_tiempo'),
    # CRUD
    path('funciones/crear/',                    views.funciones_crear,          name='funciones_crear'),
    path('funciones/<int:funcion_id>/',         views.funciones_detalle,        name='funciones_detalle'),
    path('funciones/<int:funcion_id>/editar/',  views.funciones_editar,         name='funciones_editar'),
    path('funciones/eliminar/',                 views.funciones_eliminar,       name='funciones_eliminar'),

    # ---- Reservas --------------------------------------------------------------------------------
    path('reservas/',                           views.reservas_lista,           name='reservas_lista'),
    path('reservas/<int:reserva_id>/',          views.reservas_detalle,         name='reservas_detalle'),
    path('reservas/<int:reserva_id>/editar/',   views.reservas_editar,          name='reservas_editar'),

    # ---- Pagos --------------------------------------------------------------------------------
    path('pagos/',                              views.pagos_lista,              name='pagos_lista'),
    path('pagos/estadisticas/',                 views.pagos_estadisticas,       name='pagos_estadisticas'),

    # ---- Usuarios (solo superuser) --------------------------------------------------------------------------------
    path('usuarios/',                           views.usuarios_lista,           name='usuarios_lista'),
    path('usuarios/crear/',                     views.usuarios_crear,           name='usuarios_crear'),
    path('usuarios/<int:usuario_id>/',          views.usuarios_detalle,         name='usuarios_detalle'),
    path('usuarios/<int:usuario_id>/editar/',   views.usuarios_editar,          name='usuarios_editar'),
    # ---- Verificador QR (staff) --------------------------------------------------------------------------------
    path('verificador-qr/',                     views.verificador_qr,           name='verificador_qr'),

    # ---- Promociones: Combos --------------------------------------------------------------------------------
    path('combos/',                             views.combos_lista,  name='combos_lista'),
    # CRUD
    path('combos/crear/',                       views.combos_crear,  name='combos_crear'),
    path('combos/<int:combo_id>/editar/',       views.combos_editar, name='combos_editar'),
    path('combos/eliminar/',                    views.combos_eliminar, name='combos_eliminar'),
    # ---- Promociones: Cupones --------------------------------------------------------------------------------
    path('cupones/',                            views.cupones_lista,  name='cupones_lista'),
    # CRUD
    path('cupones/crear/',                      views.cupones_crear,  name='cupones_crear'),
    path('cupones/<int:cupon_id>/editar/',      views.cupones_editar, name='cupones_editar'),
    path('cupones/eliminar/',                   views.cupones_eliminar, name='cupones_eliminar'),
    # ============================================================
    path('cupones/estadisticas/',               views.cupones_estadisticas, name='cupones_estadisticas'),
    # ============================================================
    # ---- Promociones: Promo por Día --------------------------------------------------------------------------------
    path('promociones-dia/',                    views.promodia_lista,  name='promodia_lista'),
    path('promociones-dia/crear/',              views.promodia_crear,  name='promodia_crear'),
    path('promociones-dia/<int:promo_id>/editar/', views.promodia_editar, name='promodia_editar'),
    path('promociones-dia/eliminar/',              views.promodia_eliminar, name='promodia_eliminar'),
    # ---- Cupones Usados (solo lectura) --------------------------------------------------------------------------------
    path('cupones-usados/',                     views.cupones_usados_lista, name='cupones_usados_lista'),
    # ---- Configuración General --------------------------------------------------------------------------------
    path('configuracion/',                      views.configuracion_general, name='configuracion_general'),

    # ---- Sedes (solo superuser) -------------------------------------------------------------------------------
    path('sedes/',                              views.sedes_lista,    name='sedes_lista'),
    path('sedes/crear/',                        views.sedes_crear,    name='sedes_crear'),
    path('sedes/<int:sede_id>/editar/',         views.sedes_editar,   name='sedes_editar'),
    path('sedes/eliminar/',                     views.sedes_eliminar, name='sedes_eliminar'),
    path('sedes/cambiar/',                      views.cambiar_sede_panel, name='cambiar_sede_panel'),
]