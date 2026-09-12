# Data migration: el proyecto hasta ahora era de una sola sede (todo
# global, sin modelo de ubicación). Para no perder ni tener que recargar
# a mano las salas ya cargadas en la base, se crea automáticamente una
# "Sede Principal" y se la asigna a cualquier Sala que haya quedado con
# sede=None tras el paso anterior (0011).
#
# Si en tu base ya tenías pensado un nombre/dirección real para esta
# primera sede, después de correr esta migración podés editarla desde
# el panel o el admin — esto solo evita que la migración 0013 (que hace
# el campo obligatorio) falle por filas nulas.

from django.db import migrations


def crear_y_asignar_sede_principal(apps, schema_editor):
    Sala = apps.get_model('salas', 'Sala')
    Sede = apps.get_model('sedes', 'Sede')

    if not Sala.objects.filter(sede__isnull=True).exists():
        return

    sede_principal, _ = Sede.objects.get_or_create(
        nombre='Sede Principal',
        defaults={
            'direccion': 'Completar dirección',
            'ciudad': 'Completar ciudad',
            'activa': True,
        },
    )
    Sala.objects.filter(sede__isnull=True).update(sede=sede_principal)


def revertir(apps, schema_editor):
    # No se deshace la asignación: revertir dejaría las salas sin sede,
    # lo cual rompe la migración 0011 al bajarla igual. No-op intencional.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('salas', '0011_sala_sede'),
    ]

    operations = [
        migrations.RunPython(crear_y_asignar_sede_principal, revertir),
    ]
