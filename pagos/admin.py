from django.contrib import admin
from .models import Pago

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ['numero_transaccion', 'reserva', 'metodo_pago', 'monto', 'estado', 'fecha_pago']
    list_filter = ['estado', 'metodo_pago', 'fecha_pago']
    search_fields = ['numero_transaccion', 'reserva__codigo_reserva', 'reserva__usuario__username']
    readonly_fields = ['numero_transaccion', 'fecha_pago']
    
    fieldsets = (
        ('Información de Pago', {
            'fields': ('reserva', 'monto', 'metodo_pago', 'estado')
        }),
        ('Detalles de Transacción', {
            'fields': ('numero_transaccion', 'fecha_pago', 'ultimos_4_digitos')
        }),
    )