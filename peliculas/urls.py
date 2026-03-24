from django.urls import path
from . import views

app_name = 'peliculas'

urlpatterns = [
    # URLs existentes
    path('', views.inicio, name='inicio'),
    path('peliculas/', views.lista_peliculas, name='lista_peliculas'),
    path('pelicula/<int:pelicula_id>/', views.detalle_pelicula, name='detalle_pelicula'),
    
    # NUEVAS URLs para TMDB (solo para staff)
    # path('admin/tmdb/buscar/', views.buscar_tmdb, name='buscar_tmdb'),
    # path('admin/tmdb/importar/<int:tmdb_id>/', views.importar_tmdb, name='importar_tmdb'),
    # path('admin/tmdb/actualizar/<int:pelicula_id>/', views.actualizar_desde_tmdb, name='actualizar_tmdb'),

    # URLs para TMDB (cambiar 'admin/tmdb' por 'tmdb' para evitar conflicto)
    path('tmdb/buscar/', views.buscar_tmdb, name='buscar_tmdb'),
    path('tmdb/importar/<int:tmdb_id>/', views.importar_tmdb, name='importar_tmdb'),
    path('tmdb/actualizar/<int:pelicula_id>/', views.actualizar_desde_tmdb, name='actualizar_tmdb'),

]