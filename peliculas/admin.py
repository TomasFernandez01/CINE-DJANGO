from django.contrib import admin
from .models import Pelicula


@admin.register(Pelicula)
class PeliculaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'genero', 'clasificacion', 'duracion', 'en_cartelera', 'año']
    list_filter = ['en_cartelera', 'genero', 'clasificacion', 'año']
    search_fields = ['titulo', 'director', 'actores']
    list_editable = ['en_cartelera']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('titulo', 'sinopsis', 'en_cartelera')
        }),
        ('Clasificación', {
            'fields': ('genero', 'clasificacion', 'duracion')
        }),
        ('Detalles', {
            'fields': ('director', 'actores', 'año', 'fecha_estreno')
        }),
    )