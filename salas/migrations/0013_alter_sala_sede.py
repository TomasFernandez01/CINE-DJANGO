# Paso 3 de 3: ahora que 0012 garantizó que ninguna Sala quedó con
# sede=None, se saca el null=True — sede pasa a ser realmente obligatoria,
# como está definido en salas/models.py.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salas', '0012_asignar_sede_principal'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sala',
            name='sede',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='salas',
                to='sedes.sede',
                help_text='Sede física a la que pertenece esta sala.',
            ),
        ),
    ]
