from django.urls import path
from . import views

app_name = 'salas'

urlpatterns = [
    path('salas/', views.lista_salas, name='lista_salas'),
    path('funciones/', views.lista_funciones, name='lista_funciones'),
]