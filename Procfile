# le dice a Render como arrancar el sitio.
# "web" = tipo de proceso (un servicio HTTP).
# gunicorn -->> sirve configuracion/wsgi.py::application, 
# que ya existe sin cambios --
# confirmado que WSGI_APPLICATION en settings.py apunta ahi.

# web: gunicorn configuracion.wsgi

# nuevo (Hilo 3 - Deploy): antes decia "web: gunicorn configuracion.wsgi"
# Se cambia por start.sh, que corre collectstatic y migrate  ANTES de levantar gunicorn 
web: bash start.sh