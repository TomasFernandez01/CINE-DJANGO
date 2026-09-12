# Generado a mano siguiendo el estilo de las migraciones existentes del
# proyecto (no se pudo correr "makemigrations" real: no hay Django
# instalado ni acceso a red en este entorno). Antes de aplicar en un
# entorno con Django, correr "python manage.py makemigrations --check"
# para confirmar que coincide con lo que Django hubiera generado.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Sede',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('direccion', models.CharField(max_length=200)),
                ('ciudad', models.CharField(max_length=100)),
                ('telefono', models.CharField(blank=True, max_length=30)),
                ('activa', models.BooleanField(default=True, help_text='Si está desactivada, no aparece como opción en el selector de sede del cliente.')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Sede',
                'verbose_name_plural': 'Sedes',
                'ordering': ['nombre'],
            },
        ),
    ]
