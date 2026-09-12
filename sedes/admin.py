from django.contrib import admin
from .models import Sede


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ciudad', 'direccion', 'activa']
    list_filter = ['activa', 'ciudad']
    search_fields = ['nombre', 'ciudad', 'direccion']
    list_editable = ['activa']
