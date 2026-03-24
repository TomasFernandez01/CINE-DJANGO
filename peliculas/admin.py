from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Pelicula

@admin.register(Pelicula)
class PeliculaAdmin(admin.ModelAdmin):
    
    list_display = ['titulo', 'genero', 'clasificacion', 'duracion', 'año', 'en_cartelera', 'estado_datos'] # 
    # v1 tenia += , 'tmdb_actions','tiene_datos_completos'
    # v2 tenia += , 'estado_datos' ------ no andaba con format ni marksafe
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
    
    # ============================================
    # INTEGRACIÓN CON TMDB
    # ============================================

    ########################################################################### TMDB_ACTIONS
    ########################################################################### TMDB_ACTIONS
    # def tmdb_actions(self, obj):
    #     """Botón para actualizar datos desde TMDB"""
    #     url_actualizar = reverse('peliculas:actualizar_tmdb', args=[obj.id])
    #     # Verificar si tiene datos incompletos
    #     campos_vacios = []
    #     if not obj.sinopsis:
    #         campos_vacios.append('sinopsis')
    #     if not obj.director:
    #         campos_vacios.append('director')
    #     if not obj.actores:
    #         campos_vacios.append('actores')
    #     if not obj.año:
    #         campos_vacios.append('año')
    #     if campos_vacios:
    #         title = f"Campos vacíos: {', '.join(campos_vacios)}"
    #         color = '#ffc107'  # Amarillo
    #         icon = '⚠️'
    #     else:
    #         title = 'Datos completos'
    #         color = '#28a745'  # Verde
    #         icon = '✓'
    #     return format_html(
    #         '<a href="{}" style="display: inline-block; padding: 5px 10px; background-color: {}; color: white; text-decoration: none; border-radius: 4px; font-size: 12px;" title="{}">'
    #         '{} Actualizar desde TMDB'
    #         '</a>',
    #         url_actualizar,
    #         color,
    #         title,
    #         icon
    #     )
    # tmdb_actions.short_description = 'TMDB'
    ############################################################################## v2
    # def tiene_datos_completos(self, obj):
    #     """Indica visualmente si la película tiene datos completos"""
    #     campos_vacios = []  
    #     if not obj.sinopsis:
    #         campos_vacios.append('sinopsis')
    #     if not obj.director:
    #         campos_vacios.append('director')
    #     if not obj.actores:
    #         campos_vacios.append('actores')
    #     if not obj.año:
    #         campos_vacios.append('año')
    #     if not obj.duracion:
    #         campos_vacios.append('duración')
    #     if not obj.poster:
    #         campos_vacios.append('poster')  
    #     if not campos_vacios:
    #         return format_html(
    #             '<span style="color: #28a745; font-weight: bold;">✓ Completo</span>'
    #         )
    #     else:
    #         faltantes = ', '.join(campos_vacios)
    #         return format_html(
    #             '<span style="color: #ffc107; font-weight: bold;" title="Faltan: {}">⚠️ Incompleto</span>',
    #             faltantes
    #             #url_actualizar,  # <-- ESTE ES EL PROBLEMA, no está definido
    #             #color,
    #             #title,
    #             #icon
    #         )
    # tiene_datos_completos.short_description = 'Estado'
    ############################################################################## v3
    # def estado_datos(self, obj):
    #     """Indica visualmente si la película tiene datos completos"""
    #     campos_vacios = []
    #     if not obj.sinopsis:
    #         campos_vacios.append('sinopsis')
    #     if not obj.director:
    #         campos_vacios.append('director')
    #     if not obj.actores:
    #         campos_vacios.append('actores')
    #     if not obj.año:
    #         campos_vacios.append('año')
    #     if not obj.duracion:
    #         campos_vacios.append('duración')
    #     if not obj.poster:
    #         campos_vacios.append('poster')
    #     #Antes
    #     #        '<span style="color: #28a745; font-weight: bold;">✓ Completo</span>'
    #     #        '<span style="color: #ffc107; font-weight: bold;" title="Faltan: {}">⚠️ Incompleto</span>',
    #     if not campos_vacios:
    #         return format_html(
    #             '<span style="color: #28a745; font-weight: bold;">COMPLETO</span>'
    #         )
    #     else:
    #         faltantes = ', '.join(campos_vacios)
    #         return format_html(
    #             '<span style="color: #ffc107; font-weight: bold;" title="Faltan: {}">INCOMPLETO</span>',
    #             faltantes
    #         )
    # estado_datos.short_description = 'Estado'
    ################################################################################# v4
    # def estado_datos(self, obj):
    #     """
    #     Versión simplificada que SOLO retorna texto plano. Sin format_html, sin mark_safe, sin emojis, sin nada raro.
    #     """
    #     # Contar campos vacíos
    #     vacios = 0
    #     if not obj.sinopsis:
    #         vacios += 1
    #     if not obj.director:
    #         vacios += 1
    #     if not obj.actores:
    #         vacios += 1
    #     if not obj.año:
    #         vacios += 1
    #     if not obj.duracion:
    #         vacios += 1
    #     if not obj.poster:
    #         vacios += 1
    #     # Retornar SOLO texto, sin HTML
    #     if vacios == 0:
    #         return "COMPLETO"
    #     else:
    #         return f"FALTAN {vacios}"
    # estado_datos.short_description = 'Estado'
    ################################################################################ v5?
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
    ################################################################################# TMDB_Actions
    ################################################################################# TMDB_Actions
    # ======================================================================== V 1 CHANGELIST
    # ======================================================================== V 1 CHANGELIST
    def changelist_view(self, request, extra_context=None):
        """
        Personalizar la vista de listado para agregar botón de búsqueda TMDB
        """
        extra_context = extra_context or {}
        extra_context['tmdb_search_url'] = reverse('peliculas:buscar_tmdb')
        return super().changelist_view(request, extra_context=extra_context)

    # def changelist_view(self, request, extra_context=None):
    #     """
    #     El botón de búsqueda TMDB se renderiza automáticamente
    #     en el template personalizado change_list.html
    #     """
    #     return super().changelist_view(request, extra_context=extra_context)

    # ========================================================================= V 2
    # def changelist_view(self, request, extra_context=None):
    #     """
    #     Personalizar la vista de listado para agregar botón de búsqueda TMDB
    #     """
    #     extra_context = extra_context or {}
    #     # Link al buscador de TMDB
    #     extra_context['tmdb_search_url'] = reverse('peliculas:buscar_tmdb')
    #     # Agregar botón personalizado en el header
    #     if extra_context.get('title'):
    #         extra_context['title'] = format_html(
    #             '{} <a href="{}" style="float: right; padding: 8px 15px; background-color: #01b4e4; color: white; text-decoration: none; border-radius: 4px; font-size: 14px; font-weight: bold;">🎬 Buscar en TMDB</a>',
    #             'Seleccione película para cambiar',
    #             reverse('peliculas:buscar_tmdb')
    #         )   
    #     return super().changelist_view(request, extra_context=extra_context)
    #========================================================================= V 3
    # def changelist_view(self, request, extra_context=None):
    #     """
    #     Agregar botón personalizado para buscar en TMDB
    #     """
    #     extra_context = extra_context or {}
    #     # HTML del botón que aparecerá en el admin
    #     tmdb_button = format_html(
    #         '<li>'
    #         '<a href="{}" class="addlink" style="background-color: #01b4e4; padding: 10px 15px; color: white; text-decoration: none; border-radius: 4px; display: inline-block;">'
    #         '🎬 Buscar en TMDB'
    #         '</a>'
    #         '</li>',
    #         reverse('peliculas:buscar_tmdb')
    #     )
    #     extra_context['tmdb_button'] = tmdb_button
    #     return super().changelist_view(request, extra_context=extra_context)
    #========================================================================= V 4
    #========================================================================= V 5
    #========================================================================= V 6
    """Este Debug Funciona , descomentar de ser necesario y reemplazar por el changelist actual"""
    # def changelist_view(self, request, extra_context=None):
    #     """
    #     DEBUGGING: Imprimir info de todas las películas
    #     """
    #     print("\n" + "="*60)
    #     print("🔍 DEBUGGING CHANGELIST VIEW")
    #     print("="*60)
        
    #     try:
    #         peliculas = Pelicula.objects.all()
    #         print(f"📊 Total películas en BD: {peliculas.count()}")
            
    #         for pelicula in peliculas:
    #             print(f"\n🎬 Película: {pelicula.titulo}")
    #             print(f"   - ID: {pelicula.id}")
    #             print(f"   - Título: {pelicula.titulo} (tipo: {type(pelicula.titulo)})")
    #             print(f"   - Género: {pelicula.genero} (tipo: {type(pelicula.genero)})")
    #             print(f"   - Clasificación: {pelicula.clasificacion} (tipo: {type(pelicula.clasificacion)})")
    #             print(f"   - Duración: {pelicula.duracion} (tipo: {type(pelicula.duracion)})")
    #             print(f"   - Año: {pelicula.año} (tipo: {type(pelicula.año)})")
    #             print(f"   - En cartelera: {pelicula.en_cartelera} (tipo: {type(pelicula.en_cartelera)})")
    #             print(f"   - Sinopsis: {pelicula.sinopsis[:50] if pelicula.sinopsis else 'None'}...")
    #             print(f"   - Director: {pelicula.director}")
    #             print(f"   - Actores: {pelicula.actores[:50] if pelicula.actores else 'None'}...")
    #             print(f"   - Poster: {pelicula.poster.name if pelicula.poster else 'None'}")
                
    #             # Verificar si algún campo tiene valor None o problemático
    #             campos_problematicos = []
    #             if pelicula.genero is None:
    #                 campos_problematicos.append('genero=None')
    #             if pelicula.clasificacion is None:
    #                 campos_problematicos.append('clasificacion=None')
    #             if pelicula.duracion is None:
    #                 campos_problematicos.append('duracion=None')
    #             if pelicula.año is None:
    #                 campos_problematicos.append('año=None')
                
    #             if campos_problematicos:
    #                 print(f"   ⚠️ CAMPOS PROBLEMÁTICOS: {', '.join(campos_problematicos)}")
    #             else:
    #                 print(f"   ✅ Todos los campos tienen valores")
            
    #         print("\n" + "="*60)
    #         print("✅ DEBUGGING COMPLETO - Llamando a super().changelist_view()")
    #         print("="*60 + "\n")
            
    #     except Exception as e:
    #         print(f"\n❌ ERROR EN DEBUGGING: {str(e)}")
    #         print(f"   Tipo: {type(e)}")
    #         import traceback
    #         traceback.print_exc()
    #         print("\n")
        
    #     # Agregar contexto
    #     extra_context = extra_context or {}
    #     extra_context['tmdb_search_url'] = reverse('peliculas:buscar_tmdb')
        
    #     # Llamar a la vista original
    #     return super().changelist_view(request, extra_context=extra_context)
    #========================================================================= V7?
    #========================================================================= CHANGELIST 

    #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ funciones basicas
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