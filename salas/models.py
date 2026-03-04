from django.db import models
from peliculas.models import Pelicula

class Sala(models.Model):
    nombre = models.CharField(max_length=100)
    capacidad = models.IntegerField()
    activa = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.nombre} (Cap: {self.capacidad})"
    
    class Meta:
        verbose_name = 'Sala'
        verbose_name_plural = 'Salas'
        ordering = ['nombre']


class Funcion(models.Model):
    pelicula = models.ForeignKey(Pelicula, on_delete=models.CASCADE, related_name='funciones')
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='funciones')
    fecha_hora = models.DateTimeField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.pelicula.titulo} - {self.sala.nombre} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"
    
    def asientos_disponibles(self):
        """Calcula cuántos asientos quedan disponibles"""
        # Por ahora retorna la capacidad total
        # Cuando creemos la app reservas, calcularemos los reservados
        try:
            reservados = self.reservas.aggregate(
                total=models.Sum('cantidad_entradas')
            )['total'] or 0
            return self.sala.capacidad - reservados
        except AttributeError:
            # Si todavía no existe la app reservas
            return self.sala.capacidad
    
    class Meta:
        verbose_name = 'Función'
        verbose_name_plural = 'Funciones'
        ordering = ['fecha_hora']