from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from salas.models import Funcion

class Reserva(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Pago'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('expirada', 'Expirada'),
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
    
    def esta_expirada(self):
        """Verifica si la función ya pasó y la reserva debería expirar"""
        if self.estado in ['pendiente', 'confirmada']:
            return self.funcion.fecha_hora < timezone.now()
        return False
    
    def actualizar_estado_si_expiro(self):
        """Marca como expirada si la función ya pasó"""
        if self.esta_expirada():
            self.estado = 'expirada'
            self.save(update_fields=['estado'])
            return True
        return False
    
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