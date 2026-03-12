from django.db import models
from django.utils import timezone
from datetime import timedelta
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
        try:
            reservados = self.reservas.filter(estado__in=['pendiente', 'confirmada']).aggregate(
                total=models.Sum('cantidad_entradas')
            )['total'] or 0
            return self.sala.capacidad - reservados
        except AttributeError:
            return self.sala.capacidad
    
    def esta_disponible(self):
        """Verifica si la función está disponible (no pasó y está marcada como disponible)"""
        return self.disponible and self.fecha_hora > timezone.now()
    
    def puede_cancelarse(self):
        """Verifica si falta al menos 2 horas para la función"""
        return self.fecha_hora - timezone.now() > timedelta(hours=2)
    
    def tiempo_restante(self):
        """Retorna el tiempo restante hasta la función"""
        if self.fecha_hora > timezone.now():
            delta = self.fecha_hora - timezone.now()
            horas = delta.total_seconds() / 3600
            if horas < 1:
                minutos = int(delta.total_seconds() / 60)
                return f"{minutos} minutos"
            elif horas < 24:
                return f"{int(horas)} horas"
            else:
                dias = int(horas / 24)
                return f"{dias} días"
        return "Función pasada"
    
    class Meta:
        verbose_name = 'Función'
        verbose_name_plural = 'Funciones'
        ordering = ['fecha_hora']