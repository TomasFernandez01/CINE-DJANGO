# Generado a mano (no hay Django instalado en este entorno para correr
# makemigrations — mismo caso que promociones/migrations/0003_cupon_sede_...
# .py, que documenta la misma limitación). Campo `sede` NULLABLE desde el
# principio (null=True/blank=True), así que no hace falta un paso
# intermedio en dos migraciones como pasó en salas/0011-0013 cuando un
# campo nace obligatorio.
#
# IMPORTANTE (T9): esta es la única migración de la ronda que crea un
# campo nuevo. NO se corrió — el dueño del proyecto la revisa y la corre
# él mismo con `python manage.py migrate panel`.
#
# Se usa OneToOneField (no ForeignKey) porque acá tiene que haber a lo
# sumo UNA fila de ConfiguracionGeneral por Sede — es la forma correcta
# de expresarlo en Django (ForeignKey(unique=True) genera el warning
# fields.W342 al correr makemigrations/check, sugiriendo justamente
# cambiar a OneToOneField).
#
# Qué le hace a los datos existentes: NADA les cambia. La única fila que
# hoy existe en la tabla (pk=1, la fila "global") va a quedar con
# sede=NULL después de aplicar esta migración (es el valor por default de
# un AddField nullable sobre filas ya existentes), que es exactamente el
# mismo significado que tiene "fila global" en el código nuevo de
# panel/models.py (ConfiguracionGeneral.obtener() sin argumentos la sigue
# devolviendo tal cual, con el mismo comportamiento que tenía antes de
# esta tanda). No se pierde ni se resetea ningún valor cargado.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0002_configuraciongeneral_email_backend_and_more'),
        ('sedes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuraciongeneral',
            name='sede',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='configuracion_general',
                to='sedes.sede',
                help_text=(
                    'Dejar vacío para que esta sea la configuración global de la '
                    'cadena (aplica a toda sede que no tenga su propia configuración '
                    'cargada). Elegir una sede para que estos valores apliquen solo '
                    'a esa sede, sobreescribiendo a la configuración global.'
                ),
            ),
        ),
    ]
