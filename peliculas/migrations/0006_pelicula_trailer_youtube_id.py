# Generado a mano (no hay Django instalado en este entorno para correr
# makemigrations). Campo nullable/blank desde el arranque, no hace falta
# ningún paso intermedio.
#
# IMPORTANTE: revisar y correr con `python manage.py migrate peliculas`.
# No cambia ni pierde ningún dato existente: todas las películas ya
# cargadas quedan con trailer_youtube_id=NULL (sin tráiler) hasta que se
# reimporten desde TMDB o se cargue el ID a mano en el panel.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('peliculas', '0005_historialvisto_ratingpelicula'),
    ]

    operations = [
        migrations.AddField(
            model_name='pelicula',
            name='trailer_youtube_id',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=11,
                help_text=(
                    'ID de YouTube del tráiler (los 11 caracteres después de '
                    '"v=" en la URL del video, ej: dQw4w9WgXcQ). Se completa '
                    'solo si la película se importa desde TMDB y tiene tráiler '
                    'cargado ahí; si no, se puede pegar a mano.'
                ),
            ),
        ),
    ]
