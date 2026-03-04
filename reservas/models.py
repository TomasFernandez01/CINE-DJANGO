from django.db import models
from django.contrib.auth.models import User
from salas.models import Funcion
from django.utils import timezone

class Reserva(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Pago'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservas')
    funcion = models.ForeignKey(Funcion, on_delete=models.CASCADE, related_name='reservas')
    cantidad_entradas = models.IntegerField()
    fecha_reserva = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    codigo_reserva = models.CharField(max_length=20, unique=True, blank=True)
    
    def __str__(self):
        return f"Reserva {self.codigo_reserva} - {self.usuario.username} - {self.funcion.pelicula.titulo}"
    
    def total(self):
        """Calcula el total a pagar"""
        return self.funcion.precio * self.cantidad_entradas
    
    def save(self, *args, **kwargs):
        if not self.codigo_reserva:
            # Generar código único de reserva
            import random
            import string
            self.codigo_reserva = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-fecha_reserva']