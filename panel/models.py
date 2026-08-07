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

    # modificado (Hilo 1 - Tanda D): campos que antes eran constantes hardcodeadas
    # en configuracion/settings.py, ahora editables desde el panel sin necesidad
    # de migración cada vez que cambia el número. reservas/models.py,
    # reservas/views.py y pagos/models.py leen estos valores acá primero, y si
    # por algún motivo la fila no existe todavía, caen al valor de settings.py
    # (mismo comportamiento que tenían antes).
    tiempo_limite_pago_minutos = models.PositiveIntegerField(
        default=15,
        help_text="Minutos que tiene el usuario para completar el pago desde que "
                   "entra a seleccionar asientos. Pasado ese tiempo, la reserva se "
                   "cancela automáticamente."
    )
    max_asientos_por_reserva = models.PositiveIntegerField(
        default=6,
        help_text="Cantidad máxima de asientos que un usuario puede reservar en "
                   "una sola operación."
    )
    qr_minutos_antes_funcion = models.PositiveIntegerField(
        default=120,
        help_text="Minutos antes del horario de la función en que se habilita el "
                   "escaneo del código QR de la entrada. Ejemplo: 120 = se puede "
                   "escanear desde 2 horas antes."
    )

    # ---- Integraciones ----
    tmdb_api_key = models.CharField(
        max_length=200, blank=True,
        help_text="API key de The Movie Database, usada por el importador de "
                   "películas (Panel > Películas > Buscar en TMDB). Si se deja "
                   "vacío, se usa la que esté cargada en settings.py."
    )

    # ---- Email ----
    EMAIL_BACKEND_CHOICES = [
        ('console', 'Consola (desarrollo — los mails se imprimen en la terminal, no se envían)'),
        ('smtp', 'SMTP (Gmail, Mailtrap, u otro servidor)'),
    ]
    email_backend = models.CharField(
        max_length=10, choices=EMAIL_BACKEND_CHOICES, default='console',
        help_text="Con 'Consola' no se manda ningún mail real, queda solo para "
                   "pruebas. Para mandar mails de verdad, elegí SMTP y completá "
                   "los datos de abajo."
    )
    email_host = models.CharField(max_length=200, blank=True, help_text="Ej: smtp.gmail.com o sandbox.smtp.mailtrap.io")
    email_port = models.PositiveIntegerField(null=True, blank=True, help_text="Ej: 587 (Gmail) o 2525 (Mailtrap)")
    email_use_tls = models.BooleanField(default=True)
    email_host_user = models.CharField(max_length=200, blank=True, help_text="Usuario/email de la cuenta SMTP")
    email_host_password = models.CharField(
        max_length=200, blank=True,
        help_text="Contraseña o contraseña de aplicación de la cuenta SMTP. Se "
                   "guarda como texto plano en la base de datos, igual que estaba "
                   "en settings.py — no es apto para producción real, pero sirve "
                   "para este proyecto."
    )
    email_from = models.CharField(max_length=200, blank=True, help_text="Ej: Cine Online <noreply@cineonline.com>")

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
