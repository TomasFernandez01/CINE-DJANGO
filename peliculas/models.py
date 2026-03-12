from django.db import models

class Pelicula(models.Model):
    # campos admin
    GENERO_CHOICES = [
        ('accion', 'Acción'),
        ('aventura', 'Aventura'),
        ('comedia', 'Comedia'),
        ('drama', 'Drama'),
        ('terror', 'Terror'),
        ('ciencia_ficcion', 'Ciencia Ficción'),
        ('romance', 'Romance'),
        ('thriller', 'Thriller'),
        ('animacion', 'Animación'),
        ('documental', 'Documental'),
    ]
    CLASIFICACION_CHOICES = [
        ('ATP', 'Apta para todo público'),
        ('+13', 'Mayores de 13 años'),
        ('+16', 'Mayores de 16 años'),
        ('+18', 'Mayores de 18 años'),
    ]

    # Campo basico 
    titulo = models.CharField(max_length=50, verbose_name='Titulo')
    
    # Ahora ACTIVO
    sinopsis = models.TextField(blank=True, null=True)
    duracion = models.IntegerField(help_text="Duración en minutos", blank=True, null=True)

    # Clasificación y género para CHOICES
    genero = models.CharField(max_length=20, choices=GENERO_CHOICES, blank=True, null=True)
    clasificacion = models.CharField(max_length=5, choices=CLASIFICACION_CHOICES, default='ATP')

    # Información adicional - AHORA ACTIVO
    director = models.CharField(max_length=200, blank=True, null=True)
    actores = models.TextField(blank=True, null=True, help_text="Separar actores con comas")
    año = models.IntegerField(blank=True, null=True)
    
    # Estado
    en_cartelera = models.BooleanField(default=True)
    fecha_estreno = models.DateField(blank=True, null=True)
    
    # Imagen - AHORA ACTIVO (requiere Pillow: pip install Pillow)
    poster = models.ImageField(upload_to='posters/', blank=True, null=True)

    """De esta forma se muesta con nombres y no como <Pelicula Object>"""
    def __str__(self):
        return f"{self.titulo}"
    
    # de gratis para decorar
    def duracion_formato(self):
        """Retorna duración en formato 'Xh Ymin'"""
        if self.duracion:
            horas = self.duracion // 60
            minutos = self.duracion % 60
            if horas > 0:
                return f"{horas}h {minutos}min"
            return f"{minutos}min"
        return "No especificada"

    """Correspondiente al admin de django, organiza los datos"""
    class Meta:
        verbose_name = "Pelicula"
        verbose_name_plural = "Peliculas"
        ordering = ['-en_cartelera', 'titulo']