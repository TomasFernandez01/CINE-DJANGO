from django.urls import path
from . import views

app_name = 'peliculas'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('peliculas/', views.lista_peliculas, name='lista_peliculas'),
]