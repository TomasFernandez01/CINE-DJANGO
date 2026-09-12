# Generado a mano (ver nota en sedes/migrations/0001_initial.py sobre la
# falta de Django en este entorno).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
        ('sedes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfil',
            name='sede_administrada',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='staff',
                to='sedes.sede',
                help_text='Sede que este usuario administra en el Panel. Vacío = administra todas las sedes.',
            ),
        ),
    ]
