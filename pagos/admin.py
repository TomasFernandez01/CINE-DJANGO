from django.contrib import admin
from .models import Pago, ItemPago
from django.utils.html import format_html

# modificado (combos múltiples): inline de solo lectura para ver el detalle
# de ítems (combo/bebida/snack/etc) de cada pago desde el admin
class ItemPagoInline(admin.TabularInline):
    model = ItemPago
    extra = 0
    readonly_fields = ['combo', 'cantidad', 'precio_unitario']
    can_delete = False

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = [
        'numero_transaccion', 'reserva', 'metodo_pago',
        'monto_original', 'descuento_total_display', 'monto',
        'estado', 'fecha_pago'
    ]
    list_filter = ['estado', 'metodo_pago', 'fecha_pago']
    search_fields = ['numero_transaccion', 'reserva__codigo_reserva', 'reserva__usuario__username']
    readonly_fields = [
        'numero_transaccion', 'fecha_pago',
        'monto_original', 'descuento_cupon',
        'descuento_promo_dia', 'descuento_total',
        'codigo_qr', 'fecha_escaneo',
    ]
    fieldsets = (
        ('Información de Pago', {
            'fields': ('reserva', 'metodo_pago', 'estado')
        }),
        ('Montos', {
            'fields': (
                'monto_original',
                'descuento_promo_dia',
                'descuento_cupon',
                'descuento_total',
                'precio_combo',
                'monto',
            )
        }),
        ('Promociones Aplicadas', {
            'fields': ('cupon_usado', 'combo', 'promo_dia'),
            'classes': ('collapse',),
        }),
        ('Datos de Tarjeta', {
            'fields': ('ultimos_4_digitos', 'nombre_titular'),
            'classes': ('collapse',),
        }),
        ('Transacción', {
            'fields': ('numero_transaccion', 'fecha_pago'),
        }),
        ('Código QR', {
            'fields': ('codigo_qr', 'qr_escaneado', 'fecha_escaneo', 'escaneado_por'),
            'classes': ('collapse',),
        }),
    )
 
    def descuento_total_display(self, obj):
        if obj.descuento_total and obj.descuento_total > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">-${}</span>',
                obj.descuento_total
            )
        return '—'
    descuento_total_display.short_description = 'Descuento'