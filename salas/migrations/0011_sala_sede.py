# Generado a mano (ver nota en sedes/migrations/0001_initial.py sobre la
# falta de Django en este entorno). Paso 1 de 3 para agregar sede como FK
# OBLIGATORIA a Sala sin romper las salas ya existentes en la base:
#   1) 0011 (este archivo): agrega el campo, todavía nullable.
#   2) 0012: data migration, crea "Sede Principal" y la asigna a las
#      salas que hayan quedado con sede=None.
#   3) 0013: AlterField, saca el null=True (queda obligatoria de verdad).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salas', '0010_alter_funcion_precio'),
        ('sedes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sala',
            name='sede',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='salas',
                to='sedes.sede',
                help_text='Sede física a la que pertenece esta sala.',
            ),
        ),
    ]
