from django.urls import path
from . import views

app_name = 'promociones'

urlpatterns = [
    path('mis-cupones/', views.mis_cupones, name='mis_cupones'),
    path('combos/', views.lista_combos, name='lista_combos'),
    path('api/verificar-cupon/', views.verificar_cupon_api, name='verificar_cupon'),
    path('api/promociones-dia/', views.promociones_dia_api, name='promociones_dia'),
]