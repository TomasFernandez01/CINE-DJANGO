from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from sedes.models import Sede

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    # nuevo (Sedes - Fase 3): a qué sede pertenece este usuario COMO STAFF
    # (no confundir con una futura "sede preferida" de cliente, que sería
    # otro campo). Vacío = ve/administra TODAS las sedes en el Panel
    # (pensado para superusers o un futuro rol regional). Con valor =
    # queda restringido a esa sede únicamente en Salas/Funciones/
    # Reservas/Pagos del Panel.
    sede_administrada = models.ForeignKey(
        Sede, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='staff',
        help_text="Sede que este usuario administra en el Panel. Vacío = administra todas las sedes."
    )

    def __str__(self):
        return f"Perfil de {self.user.username}"
    
    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'


# Señal para crear automáticamente el perfil cuando se crea un usuario
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)

@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    instance.perfil.save()