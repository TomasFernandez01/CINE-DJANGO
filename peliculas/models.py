from django.db import models

class Pelicula(models.Model):
    titulo = models.CharField(max_length=200)
    
    def __str__(self):
        return self.titulo
    
    class Meta:
        verbose_name = 'Película'
        verbose_name_plural = 'Películas'