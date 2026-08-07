# utils/tmdb_api.py
# Crear este archivo en: utils/tmdb_api.py

import requests
from django.conf import settings

class TMDBClient:
    """Cliente para interactuar con The Movie Database (TMDB) API"""
    
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
    
    # Mapeo de géneros TMDB a nuestros géneros
    GENERO_MAP = {
        28: 'accion',          # Action
        12: 'aventura',        # Adventure
        16: 'animacion',       # Animation
        35: 'comedia',         # Comedy
        80: 'thriller',        # Crime -> Thriller
        99: 'documental',      # Documentary
        18: 'drama',           # Drama
        10751: 'aventura',     # Family -> Aventura
        14: 'aventura',        # Fantasy -> Aventura
        36: 'drama',           # History -> Drama
        27: 'terror',          # Horror
        10402: 'drama',        # Music -> Drama
        9648: 'thriller',      # Mystery -> Thriller
        10749: 'romance',      # Romance
        878: 'ciencia_ficcion', # Science Fiction
        10770: 'drama',        # TV Movie -> Drama
        53: 'thriller',        # Thriller
        10752: 'accion',       # War -> Acción
        37: 'accion',          # Western -> Acción
    }
    
    # Mapeo de clasificaciones
    CLASIFICACION_MAP = {
        'G': 'ATP',           # General Audiences
        'PG': 'ATP',          # Parental Guidance
        'PG-13': '+13',       # Parents Strongly Cautioned
        'R': '+16',           # Restricted
        'NC-17': '+18',       # Adults Only
        'NR': 'ATP',          # Not Rated
        'TV-G': 'ATP',
        'TV-PG': 'ATP',
        'TV-14': '+13',
        'TV-MA': '+18',
    }
    
    def __init__(self, api_key=None):
        # modificado (Hilo 1 - Tanda D): prioridad ahora es: 1) api_key pasada
        # explícitamente al constructor, 2) la cargada en Panel > Configuración
        # General, 3) TMDB_API_KEY de settings.py (como estaba antes).
        if api_key is None:
            try:
                from panel.models import ConfiguracionGeneral
                api_key = ConfiguracionGeneral.obtener().tmdb_api_key or None
            except Exception:
                api_key = None
        self.api_key = api_key or getattr(settings, 'TMDB_API_KEY', None)
        if not self.api_key:
            raise ValueError("TMDB_API_KEY no está configurada en settings.py")
    
    def buscar_peliculas(self, query, page=1, language='es-ES'):
        """
        Busca películas por nombre.
        Retorna lista de resultados con datos básicos.
        """
        url = f"{self.BASE_URL}/search/movie"
        params = {
            'api_key': self.api_key,
            'query': query,
            'page': page,
            'language': language,
            'include_adult': False
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'results': data.get('results', []),
                'total_results': data.get('total_results', 0),
                'page': data.get('page', 1),
                'total_pages': data.get('total_pages', 1)
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
    
    def obtener_detalles(self, movie_id, language='es-ES'):
        """
        Obtiene detalles completos de una película por su ID de TMDB.
        Incluye créditos (director, actores).
        """
        try:
            # Obtener detalles básicos
            url_detalles = f"{self.BASE_URL}/movie/{movie_id}"
            params = {
                'api_key': self.api_key,
                'language': language,
                'append_to_response': 'credits,release_dates'
            }
            
            response = requests.get(url_detalles, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extraer información
            pelicula_data = self._extraer_datos_pelicula(data)
            
            return {
                'success': True,
                'data': pelicula_data
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extraer_datos_pelicula(self, data):
        """Extrae y formatea los datos de la película desde la respuesta de TMDB"""
        
        # Título
        titulo = data.get('title', '')
        
        # Sinopsis
        sinopsis = data.get('overview', '')
        
        # Duración en minutos
        duracion = data.get('runtime', None)
        
        # Año
        fecha_estreno = data.get('release_date', '')
        año = int(fecha_estreno.split('-')[0]) if fecha_estreno else None
        
        # Género (tomar el primero)
        generos = data.get('genres', [])
        genero = None
        if generos:
            genre_id = generos[0].get('id')
            genero = self.GENERO_MAP.get(genre_id, 'drama')
        
        # Director (desde credits)
        director = None
        credits = data.get('credits', {})
        crew = credits.get('crew', [])
        for person in crew:
            if person.get('job') == 'Director':
                director = person.get('name')
                break
        
        # Actores principales (primeros 5)
        actores = []
        cast = credits.get('cast', [])
        for actor in cast[:5]:
            actores.append(actor.get('name'))
        actores_str = ', '.join(actores) if actores else None
        
        # Clasificación (rating)
        clasificacion = 'ATP'  # Por defecto
        release_dates = data.get('release_dates', {}).get('results', [])
        for country_data in release_dates:
            if country_data.get('iso_3166_1') == 'US':  # Buscar rating de USA
                releases = country_data.get('release_dates', [])
                if releases:
                    certification = releases[0].get('certification', '')
                    clasificacion = self.CLASIFICACION_MAP.get(certification, 'ATP')
                    break
        
        # URL del poster
        poster_path = data.get('poster_path', '')
        poster_url = f"{self.IMAGE_BASE_URL}{poster_path}" if poster_path else None
        
        return {
            'titulo': titulo,
            'sinopsis': sinopsis,
            'duracion': duracion,
            'año': año,
            'genero': genero,
            'director': director,
            'actores': actores_str,
            'clasificacion': clasificacion,
            'poster_url': poster_url,
            'tmdb_id': data.get('id'),
            'vote_average': data.get('vote_average'),
            'popularity': data.get('popularity')
        }
    
    def descargar_poster(self, poster_url):
        """
        Descarga la imagen del poster desde TMDB.
        Retorna el contenido binario de la imagen.
        """
        try:
            response = requests.get(poster_url, timeout=10)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException:
            return None


# Funciones de conveniencia
def buscar_pelicula_tmdb(titulo):
    """Función helper para buscar una película"""
    try:
        client = TMDBClient()
        return client.buscar_peliculas(titulo)
    except ValueError as e:
        return {
            'success': False,
            'error': str(e),
            'results': []
        }


def importar_pelicula_tmdb(movie_id):
    """Función helper para importar una película por ID"""
    try:
        client = TMDBClient()
        return client.obtener_detalles(movie_id)
    except ValueError as e:
        return {
            'success': False,
            'error': str(e)
        }