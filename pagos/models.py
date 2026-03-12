from django.db import models
from django.utils import timezone
from reservas.models import Reserva

class Pago(models.Model):
    METODO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta_debito', 'Tarjeta de Débito'),
        ('tarjeta_credito', 'Tarjeta de Crédito'),
        ('transferencia', 'Transferencia Bancaria'),
    ]
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]
    
    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name='pago')
    metodo_pago = models.CharField(max_length=20, choices=METODO_CHOICES)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='aprobado')
    numero_transaccion = models.CharField(max_length=30, unique=True, blank=True)
    
    # Campos opcionales para tarjeta (simulados)
    ultimos_4_digitos = models.CharField(max_length=4, blank=True, null=True)
    
    def __str__(self):
        return f"Pago {self.numero_transaccion} - {self.reserva.codigo_reserva}"
    
    def save(self, *args, **kwargs):
        if not self.numero_transaccion:
            # Generar número de transacción único
            import random
            import string
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_str = ''.join(random.choices(string.digits, k=6))
            self.numero_transaccion = f"TXN{timestamp}{random_str}"
        
        # Actualizar reserva a confirmada si el pago fue aprobado
        if self.estado == 'aprobado' and self.reserva.estado == 'pendiente':
            self.reserva.estado = 'confirmada'
            self.reserva.save()
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha_pago']