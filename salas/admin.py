from django.contrib import admin
from .models import Sala, Funcion

@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'capacidad', 'activa']
    list_filter = ['activa']
    search_fields = ['nombre']
    list_editable = ['activa']


@admin.register(Funcion)
class FuncionAdmin(admin.ModelAdmin):
    list_display = ['pelicula', 'sala', 'fecha_hora', 'precio', 'disponible', 'asientos_disponibles']
    list_filter = ['disponible', 'sala', 'fecha_hora']
    search_fields = ['pelicula__titulo']
    date_hierarchy = 'fecha_hora'
    list_editable = ['disponible']
    
    def asientos_disponibles(self, obj):
        return obj.asientos_disponibles()
    asientos_disponibles.short_description = 'Asientos Disponibles'