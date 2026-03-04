from django.contrib import admin
from .models import Reserva

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['codigo_reserva', 'usuario', 'funcion', 'cantidad_entradas', 'total', 'estado', 'fecha_reserva']
    list_filter = ['estado', 'fecha_reserva']
    search_fields = ['codigo_reserva', 'usuario__username', 'funcion__pelicula__titulo']
    readonly_fields = ['codigo_reserva', 'fecha_reserva', 'total']
    list_editable = ['estado']
    
    def total(self, obj):
        return f"${obj.total()}"
    total.short_description = 'Total'