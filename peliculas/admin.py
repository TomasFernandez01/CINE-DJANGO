from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Pelicula

@admin.register(Pelicula)
class PeliculaAdmin(admin.ModelAdmin):
    
    list_display = ['titulo', 'genero', 'clasificacion', 'duracion', 'año', 'en_cartelera', 'estado_datos'] 
    list_filter = ['en_cartelera', 'genero', 'clasificacion', 'año']
    search_fields = ['titulo', 'director', 'actores']
    list_editable = ['en_cartelera']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('titulo', 'sinopsis', 'en_cartelera', 'poster')
        }),
        ('Clasificación', {
            'fields': ('genero', 'clasificacion', 'duracion')
        }),
        ('Detalles', {
            'fields': ('fecha_estreno', 'director', 'actores', 'año')
        }),
    )
    
    def estado_datos(self, obj):
        """
        Versión con colores usando format_html de forma segura.
        """
        from django.utils.html import format_html
        # Contar campos vacíos
        vacios = 0
        if not obj.sinopsis:
            vacios += 1
        if not obj.director:
            vacios += 1
        if not obj.actores:
            vacios += 1
        if not obj.año:
            vacios += 1
        if not obj.duracion:
            vacios += 1
        if not obj.poster:
            vacios += 1
        # Retornar con colores - FORMA SEGURA
        if vacios == 0:
            # Verde - completo
            return format_html(
                '<span style="color: green; font-weight: bold;">{}</span>',
                'COMPLETO'
            )
        else:
            # Naranja - incompleto
            return format_html(
                '<span style="color: orange; font-weight: bold;">{}</span>',
                f'FALTAN {vacios}'
            )
    estado_datos.short_description = 'Estado'
    
    def changelist_view(self, request, extra_context=None):
        """
        Personalizar la vista de listado para agregar botón de búsqueda TMDB
        """
        extra_context = extra_context or {}
        extra_context['tmdb_search_url'] = reverse('peliculas:buscar_tmdb')
        return super().changelist_view(request, extra_context=extra_context)

    
    def get_urls(self):
        """Agregar URL personalizada para buscar en TMDB"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'buscar-tmdb/',
                self.admin_site.admin_view(self.buscar_tmdb_view),
                name='peliculas_buscar_tmdb',
            ),
        ]
        return custom_urls + urls
    
    def buscar_tmdb_view(self, request):
        """Redirigir a la vista de búsqueda de TMDB"""
        from django.shortcuts import redirect
        return redirect('peliculas:buscar_tmdb')

    class Media:
        """Agregar CSS/JS personalizado para el botón de TMDB"""
        css = {
            'all': ('admin/css/peliculas_tmdb.css',)
        }