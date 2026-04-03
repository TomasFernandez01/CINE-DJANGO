from django.db import models
from reservas.models import Reserva
from django.utils import timezone
import uuid

class Pago(models.Model):
    METODO_PAGO_CHOICES = [
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
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    numero_transaccion = models.CharField(max_length=50, unique=True, blank=True)
    
    # Datos de tarjeta (opcional)
    ultimos_4_digitos = models.CharField(max_length=4, blank=True, null=True)
    nombre_titular = models.CharField(max_length=200, blank=True, null=True)
    
    # ============================================
    # NUEVO: CÓDIGO QR
    # ============================================
    codigo_qr = models.CharField(
        max_length=100, 
        unique=True, 
        blank=True,
        help_text="Código único para QR"
    )
    
    qr_escaneado = models.BooleanField(
        default=False,
        help_text="Indica si el QR fue escaneado al ingresar"
    )
    
    fecha_escaneo = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Fecha y hora en que se escaneó el QR"
    )
    
    escaneado_por = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Usuario/personal que escaneó el QR"
    )
    
    def __str__(self):
        return f"Pago {self.numero_transaccion} - {self.reserva.usuario.username}"
    
    def generar_codigo_qr(self):
        """-QR-. Formato: PAGO-{UUID}-{CODIGO_RESERVA}"""
        if not self.codigo_qr:
            codigo_unico = str(uuid.uuid4())[:8].upper()
            self.codigo_qr = f"CINE-{codigo_unico}-{self.reserva.codigo_reserva}"
        return self.codigo_qr
    
    def marcar_como_escaneado(self, usuario=None):
        """Marca el QR como escaneado"""
        if not self.qr_escaneado:
            self.qr_escaneado = True
            self.fecha_escaneo = timezone.now()
            if usuario:
                self.escaneado_por = usuario
            self.save(update_fields=['qr_escaneado', 'fecha_escaneo', 'escaneado_por'])
            return True
        return False
    
    def puede_escanearse(self):
        """Verifica si el QR puede ser escaneado"""
        # Verificar que no haya sido escaneado antes
        if self.qr_escaneado:
            return False, "Este código QR ya fue utilizado"
        
        # Verificar que el pago esté aprobado
        if self.estado != 'aprobado':
            return False, "El pago no está aprobado"
        
        # Verificar que la reserva esté confirmada
        if self.reserva.estado != 'confirmada':
            return False, "La reserva no está confirmada"
        
        # Verificar que la función no haya pasado
        if self.reserva.funcion.fecha_hora < timezone.now():
            return False, "La función ya pasó"
        
        # Verificar que no falte mucho para la función (máximo 2 horas antes)
        tiempo_restante = self.reserva.funcion.fecha_hora - timezone.now()
        if tiempo_restante.total_seconds() > 7200:  # 2 horas
            horas = int(tiempo_restante.total_seconds() / 3600)
            return False, f"Falta {horas} horas para la función. Llegá 30 min antes."
        
        return True, "QR válido"
    
    def save(self, *args, **kwargs):
        if not self.numero_transaccion:
            import random
            import string
            self.numero_transaccion = 'TRX-' + ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=12)
            )
        
        # Generar código QR automáticamente si el pago está aprobado
        if self.estado == 'aprobado' and not self.codigo_qr:
            self.generar_codigo_qr()
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha_pago']