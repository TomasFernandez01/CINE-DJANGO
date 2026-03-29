from django.contrib import admin
from .models import Sala, Funcion

@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'capacidad', 'filas', 'columnas', 'activa']
    list_filter = ['activa']
    search_fields = ['nombre']
    list_editable = ['activa']

    # IMPORTANTE: Capacidad es readonly (solo lectura)
    readonly_fields = ['capacidad']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'activa')
        }),
        ('Configuración de Asientos', {
            'fields': ('filas', 'columnas', 'capacidad'),
            'description': 'La capacidad se calcula automáticamente: filas × columnas'
        }),
    )
    
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
    list_display = ['pelicula', 'sala', 'fecha_hora', 'precio', 'asientos_disponibles', 'disponible']
    list_filter = ['disponible', 'sala', 'fecha_hora']
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