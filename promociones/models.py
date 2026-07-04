from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


class Cupon(models.Model):
    TIPO_CHOICES = [
        ('porcentaje', 'Porcentaje (%)'),
        ('monto_fijo', 'Monto Fijo ($)'),
    ]

    codigo = models.CharField(max_length=20, unique=True, help_text="Código único (ej: DESC25, VERANO10)")
    descripcion = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    valor = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Si es porcentaje: 25 = 25%. Si es monto fijo: 500 = $500"
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    usos_maximos = models.IntegerField(
        null=True, blank=True,
        help_text="Dejar vacío para usos ilimitados"
    )
    usos_actuales = models.IntegerField(default=0, editable=False)
    activo = models.BooleanField(default=True)
    solo_primera_compra = models.BooleanField(
        default=False,
        help_text="Solo válido para usuarios sin compras previas"
    )
    monto_minimo = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Monto mínimo de compra para poder aplicar el cupón"
    )

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"

    def es_valido(self):
        """Verifica si el cupón está vigente y tiene usos disponibles."""
        hoy = timezone.now().date()
        if not self.activo:
            return False, "Cupón inactivo"
        if hoy < self.fecha_inicio:
            return False, "El cupón aún no está vigente"
        if hoy > self.fecha_fin:
            return False, "El cupón ha expirado"
        if self.usos_maximos is not None and self.usos_actuales >= self.usos_maximos:
            return False, "El cupón alcanzó el límite de usos"
        return True, "Cupón válido"

    def calcular_descuento(self, monto):
        """Calcula el monto de descuento para un total dado."""
        monto = Decimal(str(monto))
        if self.tipo == 'porcentaje':
            return round(monto * self.valor / 100, 2)
        else:  # monto_fijo
            return min(self.valor, monto)

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.upper().strip()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Cupón'
        verbose_name_plural = 'Cupones'
        ordering = ['-fecha_inicio']


class PromocionDia(models.Model):
    TIPO_CHOICES = [
        ('2x1', '2x1 — Pagás una entrada, llevás dos'),
        ('descuento', 'Descuento porcentual'),
    ]
    DIA_CHOICES = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'),
        (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo'),
    ]

    nombre = models.CharField(max_length=100)
    dia_semana = models.IntegerField(choices=DIA_CHOICES)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    porcentaje_descuento = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text="Solo para tipo 'Descuento porcentual'"
    )
    activo = models.BooleanField(default=True)
    descripcion = models.TextField(blank=True, help_text="Descripción visible para el usuario")

    def __str__(self):
        return f"{self.nombre} ({self.get_dia_semana_display()})"

    def calcular_descuento(self, monto, cantidad_entradas):
        """
        Calcula el descuento según el tipo de promoción.
        2x1: por cada par de entradas, una es gratis.
        descuento: porcentaje sobre el total.
        """
        monto = Decimal(str(monto))
        cantidad_entradas = int(cantidad_entradas)

        if self.tipo == '2x1':
            precio_unitario = monto / cantidad_entradas
            entradas_gratis = cantidad_entradas // 2
            return round(precio_unitario * entradas_gratis, 2)
        elif self.tipo == 'descuento' and self.porcentaje_descuento:
            return round(monto * self.porcentaje_descuento / 100, 2)
        return Decimal('0')

    class Meta:
        verbose_name = 'Promoción por Día'
        verbose_name_plural = 'Promociones por Día'
        ordering = ['dia_semana']


class Combo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(
        max_length=300,
        help_text="Ej: 1 entrada + Pochoclo grande + Bebida 500ml"
    )
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)
    imagen = models.ImageField(upload_to='combos/', blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} — ${self.precio}"

    class Meta:
        verbose_name = 'Combo'
        verbose_name_plural = 'Combos'
        ordering = ['precio']


class CuponUsado(models.Model):
    cupon = models.ForeignKey(Cupon, on_delete=models.CASCADE, related_name='usos')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cupones_usados')
    reserva = models.ForeignKey(
        'reservas.Reserva',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cupon_usado'
    )
    fecha_uso = models.DateTimeField(default=timezone.now)
    descuento_aplicado = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cupon.codigo} — {self.usuario.username} ({self.fecha_uso.strftime('%d/%m/%Y')})"

    class Meta:
        verbose_name = 'Cupón Usado'
        verbose_name_plural = 'Cupones Usados'
        ordering = ['-fecha_uso']