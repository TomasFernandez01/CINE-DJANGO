from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
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
    
    # NUEVO: Fecha límite para completar el pago
    fecha_limite_pago = models.DateTimeField(null=True, blank=True)

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
    
    # ============================================
    # NUEVO: MÉTODOS PARA LÍMITE DE PAGO
    # ============================================
    
    def tiempo_restante_pago(self):
        """
        Retorna el tiempo restante para completar el pago en segundos. Retorna None si no aplica (ya pagada, cancelada, etc.)
        """
        if self.estado != 'pendiente' or not self.fecha_limite_pago:
            return None
        
        ahora = timezone.now()
        if ahora >= self.fecha_limite_pago:
            return 0
        
        delta = self.fecha_limite_pago - ahora
        return int(delta.total_seconds())
    
    def tiempo_restante_formato(self):
        """Retorna el tiempo restante en formato legible (ej: '14:32')"""
        segundos = self.tiempo_restante_pago()
        if segundos is None:
            return None
        
        if segundos <= 0:
            return "Expirado"
        
        minutos = segundos // 60
        segs = segundos % 60
        return f"{minutos:02d}:{segs:02d}"
    
    def expiro_tiempo_pago(self):
        """Verifica si expiró el tiempo para pagar"""
        if self.estado != 'pendiente':
            return False
        
        if not self.fecha_limite_pago:
            return False
        
        return timezone.now() >= self.fecha_limite_pago
    
    def cancelar_por_tiempo_expirado(self):
        """
        Cancela la reserva si expiró el tiempo de pago. Retorna True si se canceló, False si no aplicaba.
        """
        if self.expiro_tiempo_pago():
            self.estado = 'cancelada'
            self.save(update_fields=['estado'])
            return True
        return False
    
    def minutos_para_expirar(self):
        """Retorna cuántos minutos faltan para que expire"""
        segundos = self.tiempo_restante_pago()
        if segundos is None or segundos <= 0:
            return 0
        return segundos // 60

    # descomentar si falla el contador
    # def save(self, *args, **kwargs):
    #     if not self.codigo_reserva:
    #         # Generar código único de reserva
    #         import random
    #         import string
    #         self.codigo_reserva = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    #     super().save(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        if not self.codigo_reserva:
            # Generar código único de reserva
            import random
            import string
            self.codigo_reserva = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        
        # NUEVO: Establecer fecha límite de pago al crear la reserva
        if not self.pk and not self.fecha_limite_pago:
            # 15 minutos desde ahora para pagar
            self.fecha_limite_pago = timezone.now() + timedelta(minutes=5)
        
        super().save(*args, **kwargs)


    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-fecha_reserva']