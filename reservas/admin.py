from django.contrib import admin
from .models import Reserva

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['codigo_reserva', 'usuario', 'funcion', 'cantidad_entradas', 'total_display', 'estado', 'fecha_reserva']
    list_filter = ['estado', 'fecha_reserva', 'funcion__pelicula']
    search_fields = ['codigo_reserva', 'usuario__username', 'funcion__pelicula__titulo']
    readonly_fields = ['codigo_reserva', 'fecha_reserva', 'total_display']
    list_editable = ['estado']
    
    def total_display(self, obj):
        return f"${obj.total()}"
    total_display.short_description = 'Total'
    
    actions = ['marcar_como_expiradas']
    
    def marcar_como_expiradas(self, request, queryset):
        """Acción para marcar reservas como expiradas si la función ya pasó"""
        actualizadas = 0
        for reserva in queryset:
            if reserva.actualizar_estado_si_expiro():
                actualizadas += 1
        
        self.message_user(request, f'{actualizadas} reserva(s) marcada(s) como expiradas.')
    
    marcar_como_expiradas.short_description = 'Marcar como expiradas (si la función pasó)'