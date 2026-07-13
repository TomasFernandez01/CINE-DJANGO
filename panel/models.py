from django.db import models
from decimal import Decimal


class ConfiguracionGeneral(models.Model):
    """
    Configuración general del sistema, pensada como fila única (singleton).
    A propósito NO se guarda como default de un campo de modelo: si mañana
    querés cambiar el precio base de la entrada, lo editás como un dato
    normal desde el panel — no hace falta tocar código ni correr
    makemigrations/migrate cada vez que cambia el número.
    """
    precio_entrada_base = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('4500.00'),
        help_text="Precio base de una entrada, antes de aplicar el multiplicador "
                   "de la sala. Se usa solo cuando una Función no tiene un precio "
                   "manual cargado."
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración General"
        verbose_name_plural = "Configuración General"

    def __str__(self):
        return "Configuración General del Sistema"

    def save(self, *args, **kwargs):
        # Fuerza que siempre exista una única fila, con id=1.
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # no se permite borrar la configuración general

    @classmethod
    def obtener(cls):
        """Devuelve la única instancia de configuración, creándola si no existe."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

# Create your models here.
