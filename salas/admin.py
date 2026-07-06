from django.contrib import admin
from .models import Sala, Funcion

@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo_badge', 'capacidad', 'filas', 'columnas', 'activa']
    list_filter = ['activa', 'tipo']
    
    search_fields = ['nombre']
    list_editable = ['activa']
    # IMPORTANTE: Capacidad es readonly (solo lectura)
    readonly_fields = ['capacidad']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'tipo', 'activa')
        }),
        ('Configuración de Asientos', {
            'fields': ('filas', 'columnas', 'capacidad'),
            'description': 'La capacidad se calcula automáticamente: filas * columnas'
        }),
    )

    def tipo_badge(sefl, obj):
        colores = {
            '2d':         ('gray',   '🎬'),
            '3d':         ('#007bff','🥽'),
            '2d_premium': ('#fd7e14','⭐'),
            '3d_premium': ('#6f42c1','💎'),
        }
        color, icono = colores.get(obj.tipo, ('#6c757d', '🎬'))
        from django.utils.html import format_html
        return format_html(
            '<span style="background-color:{}; color:white; padding:3px 10px; '
            'border-radius:12px; font-weight:bold; font-size:12px;">{} {}</span>',
            color, icono, obj.get_tipo_display()
        )
    tipo_badge.short_description = 'Tipo'

    # Mostrar info adicional en el formulario
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            # Agregar ayuda adicional
            form.base_fields['filas'].help_text = f"Filas actuales: A hasta {chr(64 + obj.filas)}"
            form.base_fields['columnas'].help_text = f"Columnas: 1 hasta {obj.columnas}"
        return form


# @admin.register(Funcion)
# class FuncionAdmin(admin.ModelAdmin):
#     list_display = ['pelicula', 'sala', 'fecha_hora', 'precio', 'disponible', 'asientos_disponibles']
#     list_filter = ['disponible', 'sala', 'fecha_hora']
#     search_fields = ['pelicula__titulo']
#     date_hierarchy = 'fecha_hora'
#     list_editable = ['disponible']
    
#     def asientos_disponibles(self, obj):
#         return obj.asientos_disponibles()
#     asientos_disponibles.short_description = 'Asientos Disponibles'

# NUEVO --------------------------------------------------------------
@admin.register(Funcion)
class FuncionAdmin(admin.ModelAdmin):
    list_display = ['pelicula', 'sala', 'sala_tipo_badge', 'fecha_hora', 'precio', 'asientos_disponibles', 'disponible']
    list_filter = ['disponible', 'sala', 'sala__tipo', 'fecha_hora']
    search_fields = ['pelicula__titulo', 'sala__nombre']
    list_editable = ['disponible']
    date_hierarchy = 'fecha_hora'
    
    fieldsets = (
        ('Función', {
            'fields': ('pelicula', 'sala', 'fecha_hora')
        }),
        ('Precio y Disponibilidad', {
            'fields': ('precio', 'disponible')
        }),
    )

    def sala_tipo_badge(self, obj):
        colores = {
            '2d':         ('gray',   '🎬'),
            '3d':         ('#007bff','🥽'),
            '2d_premium': ('#fd7e14','⭐'),
            '3d_premium': ('#6f42c1','💎'),
        }
        color, icono = colores.get(obj.sala.tipo, ('#6c757d', '🎬'))
        from django.utils.html import format_html
        return format_html(
            '<span style="background-color:{}; color:white; padding:2px 8px; '
            'border-radius:10px; font-size:11px;">{} {}</span>',
            color, icono, obj.sala.get_tipo_display()
        )
    sala_tipo_badge.short_description = 'Tipo Sala'
    
    # Mostrar asientos disponibles en el listado
    def asientos_disponibles(self, obj):
        disponibles = obj.asientos_disponibles()
        total = obj.sala.capacidad
        porcentaje = (disponibles / total * 100) if total > 0 else 0
        
        # Color según disponibilidad
        if porcentaje > 50:
            color = 'green'
        elif porcentaje > 20:
            color = 'orange'
        else:
            color = 'red'
        
        from django.utils.html import format_html
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{} ({}%)</span>',
            color,
            disponibles,
            total,
            int(porcentaje)
        )
    asientos_disponibles.short_description = 'Disponibles'