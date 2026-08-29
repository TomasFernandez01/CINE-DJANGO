from django.db import models
from reservas.models import Reserva
from django.utils import timezone
from django.conf import settings
import uuid

def get_qr_minutos(sede=None):
    # modificado (Hilo 1 - Tanda D): antes leía solo de settings.py. Ahora se
    # prioriza el valor cargado en Panel > Configuración General (editable sin
    # migraciones); si esa fila todavía no existe, cae al valor de settings.py.
    # modificado (T11): parámetro opcional `sede` para respetar la config
    # propia de esa sede (T9) si existe.
    try:
        from panel.models import ConfiguracionGeneral
        return ConfiguracionGeneral.obtener(sede=sede).qr_minutos_antes_funcion
    except Exception:
        return getattr(settings, 'QR_MINUTOS_ANTES_FUNCION', 120)

class Pago(models.Model):
    METODO_PAGO_CHOICES = [
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
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_pago = models.DateTimeField(default=timezone.now)
    numero_transaccion = models.CharField(max_length=50, unique=True, blank=True)
    # =========================
    # MONTOS (APP PROMOCIONES)
    # =========================
    monto_original = models.DecimalField(max_digits=10,decimal_places=2,default=0,
                                         help_text="Monto antes de descuentos")
    descuento_cupon = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    descuento_promo_dia = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    descuento_total = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    precio_combo = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    cantidad_combo = models.PositiveIntegerField(default=1)
    monto = models.DecimalField(max_digits=10,decimal_places=2,
                                help_text="Monto final pagado")
    # =========================
    # DATOS TARJETA
    # =========================
    ultimos_4_digitos = models.CharField(max_length=4, blank=True, null=True)
    nombre_titular = models.CharField(max_length=200, blank=True, null=True)
    # =========================
    # APP PROMOCIONES
    # =========================
    cupon_usado = models.ForeignKey('promociones.Cupon',on_delete=models.SET_NULL,null=True,blank=True,related_name='pagos')
    combo = models.ForeignKey('promociones.Combo',on_delete=models.SET_NULL,null=True,blank=True,related_name='pagos')
    promo_dia = models.ForeignKey('promociones.PromocionDia',on_delete=models.SET_NULL,null=True,blank=True,related_name='pagos')
    # ============================================
    # QR
    # ============================================
    codigo_qr = models.CharField(max_length=100, unique=True, blank=True, 
                                 help_text="Código único para QR")
    qr_escaneado = models.BooleanField(default=False, 
                                       help_text="Indica si el QR fue escaneado al ingresar")
    fecha_escaneo = models.DateTimeField(null=True, blank=True,
                                         help_text="Fecha y hora en que se escaneó el QR")
    escaneado_por = models.CharField(max_length=100, blank=True,
                                     help_text="Usuario/personal que escaneó el QR")
    
    def __str__(self):
        return f"Pago {self.numero_transaccion} - {self.reserva.usuario.username}"
    
    def tuvo_descuento(self):
        return self.descuento_total > 0
    
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
        #tiempo_restante = self.reserva.funcion.fecha_hora - timezone.now()
        #if tiempo_restante.total_seconds() > 7200:  # 2 horas
        #    horas = int(tiempo_restante.total_seconds() / 3600)
        #    return False, f"Falta {horas} horas para la función. Llegá 30 min antes."
        #return True, "QR válido"

        # Ventana configurable: se puede escanear hasta N minutos antes
        ahora = timezone.now()
        # modificado (T11): se pasa la sede de la reserva para respetar su
        # ConfiguracionGeneral propia (T9) si existe.
        minutos_antes = get_qr_minutos(sede=self.reserva.funcion.sala.sede)
        tiempo_restante = self.reserva.funcion.fecha_hora - ahora
        segundos_limite = minutos_antes * 60
 
        if tiempo_restante.total_seconds() > segundos_limite:
            horas = int(tiempo_restante.total_seconds() / 3600)
            minutos_config = minutos_antes // 60
            return False, (
                f"Falta {horas} horas para la función. "
                f"El QR se habilita {minutos_config} hora(s) antes."
            )
 
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
        
        # MODIFICACION GEMINI: Agregar automáticamente al historial de vistas del usuario
        if self.estado == 'aprobado':
            try:
                from peliculas.models import HistorialVisto
                HistorialVisto.objects.get_or_create(
                    usuario=self.reserva.usuario,
                    pelicula=self.reserva.funcion.pelicula
                )
            except Exception:
                pass
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha_pago']

# modificado (combos múltiples): antes Pago solo podía tener UN combo (FK
# `combo` + `precio_combo` + `cantidad_combo`, arriba). Esos 3 campos se
# dejan tal cual están — por compatibilidad con los pagos ya existentes en
# la base, y como resumen rápido/legacy (se siguen completando en cada pago
# nuevo, con el primer ítem elegido y los totales sumados). Pero el detalle
# real de "qué eligió y cuánto de cada cosa" ahora vive acá, uno por cada
# ítem distinto del pedido.
class ItemPago(models.Model):
    pago = models.ForeignKey(Pago, on_delete=models.CASCADE, related_name='items')
    combo = models.ForeignKey('promociones.Combo', on_delete=models.SET_NULL, null=True, related_name='items_pago')
    cantidad = models.PositiveIntegerField(default=1)
    # snapshot del precio al momento de la compra: si el admin cambia el
    # precio del ítem después, el ticket viejo no debe cambiar retroactivamente.
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        nombre = self.combo.nombre if self.combo else '(ítem eliminado)'
        return f"{self.cantidad}x {nombre} — Pago {self.pago_id}"

    class Meta:
        verbose_name = 'Ítem de Pago'
        verbose_name_plural = 'Ítems de Pago'