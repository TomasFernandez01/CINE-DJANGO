from django.contrib import admin
from django.utils.html import format_html
from .models import Cupon, PromocionDia, Combo, CuponUsado


@admin.register(Cupon)
class CuponAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'descripcion', 'tipo', 'valor_display',
        'fecha_inicio', 'fecha_fin', 'usos_actuales', 'usos_maximos',
        'estado_display', 'activo'
    ]
    list_filter = ['activo', 'tipo', 'solo_primera_compra']
    search_fields = ['codigo', 'descripcion']
    # list_editable = ['activo']
    readonly_fields = ['usos_actuales']

    fieldsets = (
        ('Información del Cupón', {
            'fields': ('codigo', 'descripcion', 'activo')
        }),
        ('Descuento', {
            'fields': ('tipo', 'valor', 'monto_minimo')
        }),
        ('Vigencia', {
            'fields': ('fecha_inicio', 'fecha_fin')
        }),
        ('Restricciones', {
            'fields': ('usos_maximos', 'usos_actuales', 'solo_primera_compra')
        }),
    )

    def valor_display(self, obj):
        if obj.tipo == 'porcentaje':
            return f"{obj.valor}%"
        return f"${obj.valor}"
    valor_display.short_description = 'Descuento'
    # .las funciones que user FORMAT daran error por lo tanto pasarlo a str plano
    # def estado_display(self, obj):
    #     valido, mensaje = obj.es_valido()
    #     if valido:
    #         return format_html('<span style="color:green; font-weight:bold;">✓ Vigente</span>')
    #     return format_html(
    #         '<span style="color:red; font-weight:bold;" title="{}">'
    #         '✗ No válido</span>', mensaje
    #     )
    # estado_display.short_description = 'Estado'
    def estado_display(self, obj):
        from django.utils import timezone
        hoy = timezone.now().date()
        if not obj.activo:
            return 'Inactivo'
        if obj.fecha_fin and hoy > obj.fecha_fin:
            return 'Expirado'
        if obj.usos_maximos and obj.usos_actuales >= obj.usos_maximos:
            return 'Sin usos'
        return 'Vigente'
    estado_display.short_description = 'Estado'

@admin.register(PromocionDia)
class PromocionDiaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'dia_semana_display', 'tipo', 'detalle_promo', 'activo']
    list_filter = ['activo', 'tipo', 'dia_semana']
    # list_editable = ['activo']

    fieldsets = (
        ('Información', {
            'fields': ('nombre', 'descripcion', 'activo')
        }),
        ('Configuración', {
            'fields': ('dia_semana', 'tipo', 'porcentaje_descuento')
        }),
    )

    def dia_semana_display(self, obj):
        return obj.get_dia_semana_display()
    dia_semana_display.short_description = 'Día'

    def detalle_promo(self, obj):
        if obj.tipo == '2x1':
            return '2x1 (50% entradas pares)'
        if obj.tipo == 'descuento' and obj.porcentaje_descuento:
            return f'{obj.porcentaje_descuento}% de descuento'
        return '—'
    detalle_promo.short_description = 'Detalle'


@admin.register(Combo)
class ComboAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion', 'precio', 'activo', 'tiene_imagen']
    list_filter = ['activo']
    # list_editable = ['activo', 'precio']
    search_fields = ['nombre', 'descripcion']
    # def tiene_imagen(self, obj):
    #     if obj.imagen:
    #         return format_html('<span style="color:green;">✓</span>')
    #         return format_html('<span>ok</span>')
    #     return format_html('<span style="color:#ccc;">—</span>')
    #     return format_html('<span>guion</span>')
    fieldsets = (
        ('Información', {
            'fields': ('nombre', 'descripcion', 'activo')
        }),
        ('Precio e Imagen', {
            'fields': ('precio', 'imagen')
        }),
    )
    def tiene_imagen(self, obj):
        return 'Si' if obj.imagen else 'No'
    tiene_imagen.short_description = 'Imagen'


@admin.register(CuponUsado)
class CuponUsadoAdmin(admin.ModelAdmin):
    list_display = ['cupon', 'usuario', 'reserva', 'descuento_aplicado', 'fecha_uso']
    list_filter = ['cupon', 'fecha_uso']
    search_fields = ['cupon__codigo', 'usuario__username']
    readonly_fields = ['cupon', 'usuario', 'reserva', 'fecha_uso', 'descuento_aplicado']

    def has_add_permission(self, request):
        return False  # Los usos se registran automáticamente