# peliculas/management/commands/importar_peliculas_tmdb.py
# Colocar en: peliculas/management/commands/importar_peliculas_tmdb.py

from django.core.management.base import BaseCommand
from peliculas.models import Pelicula
from django.core.files.base import ContentFile
import requests

try:
    from utils.tmdb_api import buscar_pelicula_tmdb, importar_pelicula_tmdb
    TMDB_DISPONIBLE = True
except ImportError:
    TMDB_DISPONIBLE = False

##################################################### Nuevo v1
def descargar_poster(poster_url, titulo):
    """Descarga el poster desde TMDB"""
    try:
        response = requests.get(poster_url, timeout=10)
        response.raise_for_status()
        nombre_archivo = f"{titulo.lower().replace(' ', '_')[:50]}.jpg"
        return ContentFile(response.content, name=nombre_archivo)
    except Exception as e:
        print(f"Error descargando poster: {e}")
        return None
#####################################################

class Command(BaseCommand):
    help = 'Importa películas desde TMDB usando una lista de títulos'

    def add_arguments(self, parser):
        parser.add_argument(
            'titulos',
            nargs='+',
            type=str,
            help='Lista de títulos de películas a buscar e importar'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la importación sin guardar en la base de datos',
        )
        #################################################### Nuevo parser v1
        parser.add_argument(
            '--sin-posters',
            action='store_true',
            help='No descargar posters (solo datos)',
        )
        #####################################################
    def handle(self, *args, **options):
        if not TMDB_DISPONIBLE:
            self.stdout.write(self.style.ERROR('❌ TMDB no está configurado'))
            return
        
        titulos = options['titulos']
        dry_run = options['dry_run']
        # nuevo
        sin_posters = options['sin_posters']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODO DRY-RUN: No se guardará nada'))
            self.stdout.write('')
        # nuevo
        if sin_posters:
            self.stdout.write(self.style.WARNING('📷 Posters deshabilitados'))
            self.stdout.write('')

        importadas = 0
        ya_existentes = 0
        errores = 0
        
        for titulo in titulos:
            self.stdout.write(f'🔍 Buscando: "{titulo}"...')
            
            # Buscar en TMDB
            response = buscar_pelicula_tmdb(titulo)
            
            if not response['success']:
                self.stdout.write(self.style.ERROR(f'   ❌ Error: {response.get("error")}'))
                errores += 1
                continue
            
            results = response['results']
            
            if not results:
                self.stdout.write(self.style.WARNING(f'   ⚠️ No se encontraron resultados'))
                errores += 1
                continue
            
            # Tomar el primer resultado (más relevante)
            primera = results[0]
            tmdb_id = primera['id']
            titulo_encontrado = primera['title']
            
            self.stdout.write(f'   ✓ Encontrada: "{titulo_encontrado}" (ID: {tmdb_id})')
            
            # Verificar si ya existe
            if Pelicula.objects.filter(titulo__iexact=titulo_encontrado).exists():
                self.stdout.write(self.style.WARNING(f'   ⚠️ Ya existe en la base de datos'))
                ya_existentes += 1
                continue
            
            # Obtener detalles completos
            detalles_response = importar_pelicula_tmdb(tmdb_id)
            
            if not detalles_response['success']:
                self.stdout.write(self.style.ERROR(f'   ❌ Error al obtener detalles'))
                errores += 1
                continue
            
            data = detalles_response['data']
            
            if not dry_run:
                # Crear la película
                pelicula = Pelicula.objects.create(
                    titulo=data['titulo'][:50],
                    sinopsis=data.get('sinopsis', ''),
                    duracion=data.get('duracion'),
                    genero=data.get('genero'),
                    clasificacion=data.get('clasificacion', 'ATP'),
                    director=data.get('director', ''),
                    actores=data.get('actores', ''),
                    año=data.get('año'),
                    en_cartelera=False,
                )
                
                # NUEVO: Descargar poster automáticamente
                poster_descargado = False
                if not sin_posters and data.get('poster_url'):
                    self.stdout.write(f'   📷 Descargando poster...')
                    poster_file = descargar_poster(data['poster_url'], data['titulo'])
                    if poster_file:
                        pelicula.poster.save(poster_file.name, poster_file, save=False)
                        poster_descargado = True
                        self.stdout.write(self.style.SUCCESS(f'   ✅ Poster descargado'))
                    else:
                        self.stdout.write(self.style.WARNING(f'   ⚠️ No se pudo descargar el poster'))
                
                pelicula.save()
                
                if poster_descargado:
                    self.stdout.write(self.style.SUCCESS(f'   ✅ Importada con poster: {pelicula.titulo}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'   ✅ Importada sin poster: {pelicula.titulo}'))

                # self.stdout.write(self.style.SUCCESS(f'   ✅ Importada: {pelicula.titulo}'))
                importadas += 1
            else:
                # Modo dry-run
                self.stdout.write(self.style.SUCCESS(f'   ✅ Se importaría: {data["titulo"]}'))
                self.stdout.write(f'      - Director: {data.get("director", "N/A")}')
                self.stdout.write(f'      - Año: {data.get("año", "N/A")}')
                self.stdout.write(f'      - Duración: {data.get("duracion", "N/A")} min')
                if data.get('poster_url') and not sin_posters:
                    self.stdout.write(f'      - Poster: Disponible ✓')
                importadas += 1
            
            self.stdout.write('')
        
        # Resumen
        self.stdout.write(self.style.SUCCESS('='*60))
        if dry_run:
            self.stdout.write(self.style.WARNING(f'📊 RESUMEN (SIMULACIÓN):'))
        else:
            self.stdout.write(self.style.SUCCESS(f'📊 RESUMEN:'))
        self.stdout.write(f'   ✅ Importadas: {importadas}')
        self.stdout.write(f'   ⚠️ Ya existentes: {ya_existentes}')
        self.stdout.write(f'   ❌ Errores: {errores}')
        # nuevo
        if not sin_posters:
            self.stdout.write(f'   📷 Posters: Descargados automáticamente')
        # nuevo
        self.stdout.write(self.style.SUCCESS('='*60))


# Ejemplo de uso:
# python manage.py importar_peliculas_tmdb "Inception" "Pulp Fiction" "The Matrix"
# python manage.py importar_peliculas_tmdb "Parasite" "Joker" --dry-run