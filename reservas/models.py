from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from salas.models import Funcion
from django.conf import settings

def get_tiempo_limite():
    return getattr(settings, 'TIEMPO_LIMITE_PAGO_MINUTOS', 15)

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

    # NUEVO: Campo para guardar los asientos seleccionados
    asientos_seleccionados = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        help_text="Asientos separados por coma. Ej: A1,A2,B5"
    )

    def __str__(self):
        return f"Reserva {self.codigo_reserva} - {self.usuario.username} - {self.funcion.pelicula.titulo}"
    
    def total(self):
        """
        Calcula el total a pagar por las entradas. Si hay asientos guardados,
        suma el precio de CADA asiento (funcion.precio_para_asiento), que ya
        tiene en cuenta el multiplicador de la sala y el de la categoría del
        asiento si tiene una (ej: "Mejorado"). Si por algún motivo no hay
        asientos guardados (reservas viejas, o casos sin mapa), cae al
        cálculo plano anterior como respaldo.
        """
        asientos = self.lista_asientos()
        if asientos:
            return sum(
                (self.funcion.precio_para_asiento(codigo) for codigo in asientos),
                Decimal('0')
            )
        return self.funcion.precio_final() * self.cantidad_entradas
        return self.funcion.precio * self.cantidad_entradas
    #-------------------------------------------------------------
                                #PROMOCIONES 
    
    def total_pagado(self):
        """Retorna el monto real pagado. Si hay pago con descuento, usa pago.monto."""
        if hasattr(self, 'pago'):
            return self.pago.monto
        return self.total()

    def tuvo_descuento(self):
        """Indica si se aplicó algún descuento al pago."""
        if hasattr(self, 'pago'):
            return self.pago.descuento_total > 0
        return False
    #-------------------------------------------------------------
    
    ##############################################################3
    def desglose_precios_asientos(self):
        """
        Lista de {codigo, precio} para cada asiento de esta reserva, usando el
        precio real de CADA asiento (con su categoría especial si tiene).
        Sirve para mostrar un desglose cuando no todos cuestan lo mismo.
        """
        return [
            {'codigo': codigo, 'precio': self.funcion.precio_para_asiento(codigo)}
            for codigo in self.lista_asientos()
        ]

    def tiene_precios_mixtos(self):
        """True si esta reserva tiene asientos con precios distintos entre sí
        (por categorías especiales tipo "Mejorado")."""
        precios = {item['precio'] for item in self.desglose_precios_asientos()}
        return len(precios) > 1

    def lista_asientos(self):
        """Retorna los asientos como lista"""
        if self.asientos_seleccionados:
            return self.asientos_seleccionados.split(',')
        return []
    
    def asientos_formateados(self):
        """Retorna los asientos en formato legible"""
        if self.asientos_seleccionados:
            asientos = self.asientos_seleccionados.split(',')
            if len(asientos) <= 5:
                return ', '.join(asientos)
            else:
                return f"{', '.join(asientos[:5])} y {len(asientos) - 5} más"
        return "Sin asientos asignados"
    ################################################################

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
        
        return int((self.fecha_limite_pago - ahora).total_seconds())
        #antes
        #delta = self.fecha_limite_pago - ahora
        #return int(delta.total_seconds())
    
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
        #if not self.pk and not self.fecha_limite_pago:
            # 15 minutos desde ahora para pagar
            #self.fecha_limite_pago = timezone.now() + timedelta(minutes=5)
        # NUEVO: Validar que la cantidad de asientos coincida
        #if self.asientos_seleccionados:
            #cantidad_seleccionados = len(self.asientos_seleccionados.split(','))
            #if cantidad_seleccionados != self.cantidad_entradas:
                #self.cantidad_entradas = cantidad_seleccionados

        # Establecer fecha límite usando la constante de settings
        # Si se pasa fecha_limite_pago desde la view (calculada desde inicio de selección) se respeta,
        # si no existe, se calcula desde ahora como fallback
        if not self.pk and not self.fecha_limite_pago:
            self.fecha_limite_pago = timezone.now() + timedelta(minutes=get_tiempo_limite()) 
        # Sincronizar cantidad_entradas con asientos_seleccionados
        if self.asientos_seleccionados:
            cantidad_seleccionados = len(self.asientos_seleccionados.split(','))
            if cantidad_seleccionados != self.cantidad_entradas:
                self.cantidad_entradas = cantidad_seleccionados

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-fecha_reserva']