#!/usr/bin/env bash
# nuevo (Hilo 3 - Deploy): Render Free no da acceso a Shell, asi que las
# migraciones no se pueden correr a mano despues del deploy como en el
# plan pago. Este script reemplaza al Start Command directo de gunicorn:
# corre collectstatic y migrate PRIMERO, y recien despues levanta el
# servidor. Se ejecuta en cada deploy (o sea, en cada `migrate` -- si no
# hay migraciones nuevas pendientes, Django no hace nada y sigue de largo
# sin romper nada).
#
# 'set -o errexit' corta el script si cualquier comando de los de abajo
# falla (ej. un error en una migracion) -- asi el deploy queda marcado
# como fallido en vez de levantar un sitio roto silenciosamente.
set -o errexit

# DIAGNOSTICO TEMPORAL v3 (Hilo 3 - Deploy): -v 3 no mostro nada nuevo
# porque no hay nada que "copiar" si los finders no encuentran ningun
# archivo -- el problema es ANTES de esa etapa. Ahora inspeccionamos
# directamente que valor tiene STATICFILES_DIRS en tiempo real dentro de
# Django, y que devuelve cada finder por separado.
echo "== DIAGNOSTICO: inspeccion directa de finders =="
python manage.py shell -c "
from django.conf import settings
from django.contrib.staticfiles.finders import get_finders
print('STATICFILES_DIRS =', settings.STATICFILES_DIRS)
print('STATIC_ROOT =', settings.STATIC_ROOT)
print('STATICFILES_STORAGE =', getattr(settings, 'STATICFILES_STORAGE', None))
print('STORAGES =', getattr(settings, 'STORAGES', None))
total = 0
for finder in get_finders():
    print('--- Finder:', finder.__class__.__module__ + '.' + finder.__class__.__name__)
    count = 0
    for path, storage in finder.list(None):
        count += 1
        if count <= 5:
            print('   ->', path)
    print('   total encontrados por este finder:', count)
    total += count
print('TOTAL GENERAL:', total)
"
echo "== FIN DIAGNOSTICO =="

echo "== collectstatic =="
python manage.py collectstatic --noinput

echo "== migrate =="
python manage.py migrate --noinput

# nuevo: crea un superusuario la primera vez, leyendo credenciales de las
# variables de entorno DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD.
# Es la funcionalidad NATIVA de Django (createsuperuser --noinput ya sabe
# leer esas 3 variables solo, no hace falta escribir nada custom). Hace
# falta esto porque el plan Free de Render no da Shell para correr
# `python manage.py createsuperuser` a mano.
#
# El '|| echo ...' al final es a proposito: si el usuario YA existe (por
# ejemplo, en el segundo deploy en adelante), este comando normalmente
# fallaria con "Error: That username is already taken." y cortaria todo
# el script por el 'set -o errexit' de arriba. Con el '||' se evita eso:
# si falla (porque ya existe, o porque no cargaste las 3 variables),
# simplemente lo avisa por log y sigue de largo sin frenar el deploy.
echo "== createsuperuser (si no existe todavia) =="
python manage.py createsuperuser --noinput || echo "Superusuario ya existe o faltan las variables DJANGO_SUPERUSER_*, se omite este paso"

echo "== arrancando gunicorn =="
# 'exec' reemplaza el proceso del script por gunicorn (en vez de dejarlo
# corriendo como proceso hijo) -- es lo que espera Render para poder
# mandarle señales de apagado/reinicio correctamente.
exec gunicorn configuracion.wsgi
