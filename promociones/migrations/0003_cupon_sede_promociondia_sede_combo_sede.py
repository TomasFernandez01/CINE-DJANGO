# Generado a mano (ver nota en sedes/migrations/0001_initial.py sobre la
# falta de Django en este entorno). Campo sede NULLABLE en los 3 modelos:
# no hace falta un paso intermedio como en salas/0011-0013 porque acá el
# campo nace opcional (null=True desde el principio, no obligatorio).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('promociones', '0002_combo_categoria'),
        ('sedes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cupon',
            name='sede',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='cupones',
                to='sedes.sede',
                help_text='Dejar vacío para que el cupón sea válido en todas las sedes. Elegir una sede para que sea exclusivo de esa sede.',
            ),
        ),
        migrations.AddField(
            model_name='promociondia',
            name='sede',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='promociones_dia',
                to='sedes.sede',
                help_text='Dejar vacío para que la promoción aplique en todas las sedes. Elegir una sede para que sea exclusiva de esa sede.',
            ),
        ),
        migrations.AddField(
            model_name='combo',
            name='sede',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='combos',
                to='sedes.sede',
                help_text='Dejar vacío para que el ítem esté disponible en todas las sedes. Elegir una sede para que sea exclusivo de esa sede.',
            ),
        ),
    ]
