from django.contrib import admin
from .models import Pelicula

@admin.register(Pelicula)
class PeliculaAdmin(admin.ModelAdmin):
    list_display = ['titulo']
    search_fields = ['titulo']