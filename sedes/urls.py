from django.urls import path
from . import views

app_name = 'sedes'

urlpatterns = [
    path('sedes/cambiar/', views.cambiar_sede, name='cambiar_sede'),
]
