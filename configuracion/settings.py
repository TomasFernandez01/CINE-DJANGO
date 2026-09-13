from pathlib import Path
import os
# modificado (Hilo 2 - Google Sign-In): carga de variables desde un archivo
# .env (NO se commitea, ver .gitignore). Se usa acá solo para las
# credenciales de Google OAuth (GOOGLE_CLIENT_ID/SECRET) -- el resto de
# settings.py (SECRET_KEY, TMDB_API_KEY, etc.) queda igual que antes, eso
# es alcance del Hilo 3 (deploy), no de este hilo. Requiere python-dotenv,
# agregado a requirements.txt.
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')  # modificado (Hilo 2)

# modificado: SECRET_KEY ahora se lee de .env. Se deja el valor viejo como
# fallback SOLO para que no se rompa si alguien clona el repo sin .env
# todavía -- pero ese valor YA ESTÁ en el historial de git si se llegó a
# commitear antes, así que no sirve como secreto real de acá en más.
# Recomendado: generar una SECRET_KEY nueva para producción (Hilo 3) y
# ponerla en el .env real, nunca acá.
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
)

# modificado (Hilo 3 - Deploy): antes era `DEBUG = True` fijo. Ahora se lee
# de la variable de entorno DEBUG, con default 'False' -- si alguien se
# olvida de setearla en Render, el sitio NO queda abierto en modo debug por
# accidente. En desarrollo local, poner DEBUG=True en el .env si se quiere
# ver el traceback completo de Django.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# modificado (Hilo 3 - Deploy): antes era `[]` fijo (bloquea cualquier
# deploy real). Ahora se lee de la variable de entorno ALLOWED_HOSTS, una
# lista separada por comas (ej. "midominio.onrender.com,www.midominio.com").
# En local, si no se setea nada, queda una lista vacía -- Django igual deja
# pasar localhost/127.0.0.1 cuando DEBUG=True, así que no rompe el
# desarrollo de nadie.
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()]

# nuevo (Hilo 3 - Deploy): Django exige el esquema completo (https://) acá
# desde hace varias versiones, no alcanza con el dominio pelado como en
# ALLOWED_HOSTS. Mismo criterio: separado por comas en la env var, ej.
# "https://midominio.onrender.com,https://www.midominio.com".
CSRF_TRUSTED_ORIGINS = [h.strip() for h in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if h.strip()]

APPS = [
    'sedes',
    'peliculas',
    'salas',        
    'reservas',
    'usuarios',
    'pagos',
    'panel',
    'promociones',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    # modificado (Hilo 3 - Deploy): cloudinary_storage y cloudinary van ANTES
    # de django.contrib.staticfiles -- es el orden que pide la librería
    # django-cloudinary-storage para que funcione el storage de media.
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',
    # modificado (Hilo 2 - Google Sign-In): django.contrib.sites es requisito
    # de allauth (usa SITE_ID más abajo). Las 4 siguientes son allauth en sí
    # + el provider de Google puntual (no se instalan otros providers).
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
] + APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # nuevo (Hilo 3 - Deploy): sirve los estáticos ya comprimidos/hasheados
    # en producción (Render no tiene un servidor de estáticos aparte como
    # Nginx). Tiene que ir justo después de SecurityMiddleware, es el orden
    # que pide la propia documentación de Whitenoise.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # modificado (Hilo 2 - Google Sign-In): requerido por django-allauth
    # >=0.53 (versión pineada en requirements.txt). Si Tomás instala una
    # versión más vieja que no lo necesite, esta línea no debería romper
    # nada -- pero avisar si el pip install tira ImportError acá.
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'configuracion.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # nuevo (Sedes - Fase 2): expone sede_actual/sedes_disponibles
                # a todos los templates para el selector "Elegí tu cine".
                'sedes.context_processors.sede_actual',
                # nuevo (Sedes - Fase 3): equivalente para el Panel (sede
                # fija/activa/disponibles del staff logueado).
                'panel.context_processors.sede_panel_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'configuracion.wsgi.application'

# modificado (Hilo 3 - Deploy): Render no persiste el filesystem entre
# deploys, así que SQLite no sirve en producción -- hay que usar el
# Postgres que da Render. Si existe la variable de entorno DATABASE_URL
# (Render la inyecta sola al conectar la base), se usa esa. Si no existe
# (entorno de desarrollo local de cualquiera del equipo), se cae a SQLite
# como siempre -- nadie tiene que tocar su .env local por este cambio.
# Requiere dj-database-url, agregado a requirements.txt.
import dj_database_url  # modificado (Hilo 3 - Deploy)

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es-ar'

# TIME_ZONE = 'UTC'
TIME_ZONE = 'America/Argentina/Buenos_Aires'

USE_I18N = True

USE_TZ = True

# STATIC_URL = 'static/'
STATIC_URL = '/static/'

# nuevo: se registra la carpeta static/ del proyecto para poder separar CSS/JS de los templates
STATICFILES_DIRS = [BASE_DIR / 'static']

# nuevo (Hilo 3 - Deploy): carpeta donde `collectstatic` junta TODOS los
# estáticos del proyecto para producción -- no confundir con
# STATICFILES_DIRS de arriba (esa es la carpeta de origen del código
# fuente, esta es la de destino generada). Ya está en .gitignore.

# STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') 

# nuevo (Hilo 3 - Deploy): storage recomendado por la propia documentación
# de Whitenoise para producción -- sirve los estáticos comprimidos y con
# un hash en el nombre de archivo (cache-busting automático al cambiar CSS/JS).
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# para que en los modelos no tenga q especificar ID auto incremental
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# modificado (Hilo 2 - Google Sign-In): se agrega el backend de allauth
# SIN sacar el backend estándar de Django -- el login usuario/contraseña
# (usuarios/views.py::login_view, que ya funciona a mano con authenticate())
# sigue funcionando exactamente igual que antes.
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# modificado (Hilo 2 - Google Sign-In): requerido por django.contrib.sites
# (dependencia de allauth). Con un solo sitio (este proyecto), SITE_ID=1 alcanza.
SITE_ID = 1

# Login settings
#LOGIN_URL = '/admin/login/'
#LOGIN_REDIRECT_URL = '/'
#LOGOUT_REDIRECT_URL = '/'
# nuevo
LOGIN_URL = 'usuarios:login'
LOGIN_REDIRECT_URL = 'peliculas:inicio'
LOGOUT_REDIRECT_URL = 'peliculas:inicio'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# modificado (Hilo 3 - Deploy): Render borra el filesystem local en cada
# redeploy, así que las imágenes subidas (posters de películas, imágenes
# de combos, etc.) se pierden si se dejan en disco -- por eso se cambia el
# storage a Cloudinary. MEDIA_ROOT/MEDIA_URL de arriba quedan sin uso real
# en producción (Cloudinary maneja sus propias URLs), pero no se borran
# para no romper nada si algún día se vuelve a filesystem local.
# Esto cambia el storage de TODOS los ImageField/FileField existentes
# (Pelicula.poster, Combo.imagen) sin tener que tocar los modelos --
# es puramente config de acá. Requiere django-cloudinary-storage y
# cloudinary, agregados a requirements.txt.
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# ============================================
# CONFIGURACIÓN DE EMAIL - Agregar al final de settings.py
# ============================================

# Opción 1: GMAIL (Desarrollo y Producción)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
# modificado (revisión final): antes era f"DJANGO-CINE <{EMAIL_HOST_USER}>"
# directo -- si en algún entorno falta la variable EMAIL_HOST_USER (.env
# incompleto, compu de otro compañero, Render antes de cargar las env
# vars), esto quedaba como "DJANGO-CINE <None>", un remitente roto. Ahora
# cae a un string fijo en ese caso -- no soluciona que falte configurar el
# email, pero evita el remitente inválido.
DEFAULT_FROM_EMAIL = f"DJANGO-CINE <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else 'DJANGO-CINE <noreply@localhost>'

# Opción 2: CONSOLE (Solo para desarrollo/testing - imprime en consola)
# Descomenta esto si querés probar sin configurar email real
#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Opción 3: Mailtrap (Recomendado para desarrollo)
# Registrate gratis en https://mailtrap.io
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'sandbox.smtp.mailtrap.io'
# EMAIL_PORT = 2525
# EMAIL_HOST_USER = 'tu-usuario-mailtrap'
# EMAIL_HOST_PASSWORD = 'tu-password-mailtrap'
# EMAIL_USE_TLS = True
# DEFAULT_FROM_EMAIL = 'Cine Online <noreply@cineonline.com>'

# ============================================
# FIN CONFIGURACIÓN EMAIL
# ============================================
# Ver si los emails se están enviando:
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.core.mail': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
# ============================================
# CONFIGURACIÓN TMDB API
# ============================================
# modificado: TMDB_API_KEY ahora se lee de .env, mismo criterio y misma
# advertencia que SECRET_KEY arriba (el valor hardcodeado queda de
# fallback, pero ya no es un secreto real si estuvo commiteado antes).
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')

# Minutos que tiene el usuario para completar el pago
# (se cuenta desde que entra a seleccionar asientos)
TIEMPO_LIMITE_PAGO_MINUTOS = 15
 
# Máximo de asientos que puede reservar un usuario en una sola reserva
MAX_ASIENTOS_POR_RESERVA = 6
 
# Minutos antes de la función en que se habilita el escaneo del QR
# Ejemplo: 120 = se puede escanear hasta 2 horas antes
QR_MINUTOS_ANTES_FUNCION = 120

# ============================================================
# modificado (Hilo 2 - Google Sign-In): configuración de allauth + Google
# ============================================================

# Client ID / Secret de Google Cloud Console (los genera Tomás, ver
# reportes/delegacion/delegacion_v3.md Hilo 2). NUNCA hardcodear acá --
# van en un archivo .env en la raíz del proyecto (agregar .env al
# .gitignore si todavía no está, para no commitear secretos):
#   GOOGLE_CLIENT_ID=...
#   GOOGLE_CLIENT_SECRET=...
# Mientras no estén cargadas, quedan vacías y el botón de Google va a
# fallar al clickearlo (no rompe el resto del sitio, solo esa acción).
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
            'key': '',
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

# nuevo (Hilo 2 - Google Sign-In): adapter propio (usuarios/adapters.py) que
# vincula la cuenta de Google a un User existente con el mismo email en vez
# de duplicar el usuario o tirar error -- ver punto pedido en
# delegacion_v3.md ("un usuario que ya se registró con contraseña pueda
# vincular su cuenta de Google después, sin duplicar el usuario").
SOCIALACCOUNT_ADAPTER = 'usuarios.adapters.CustomSocialAccountAdapter'

# Decisión de interpretación (documentada en el reporte): 'none' en vez de
# 'mandatory'/'optional'. El registro propio (RegistroForm) tampoco exige
# verificar el email hoy, así que esto mantiene el mismo nivel de exigencia
# entre ambos flujos de alta. Además, el envío de verificación depende de
# que el Hilo 1 (Gmail SMTP) ya esté andando, y no se quiso acoplar el
# login social a esa dependencia.
ACCOUNT_EMAIL_VERIFICATION = 'none'

# El email de Google ya viene validado por Google -- no hace falta que
# allauth pida confirmarlo de nuevo para cuentas sociales.
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'

# Auto-crea el User la primera vez que alguien entra con Google (nombre,
# apellido y email se completan solos desde el perfil de Google -- no hace
# falta pedir nada aparte, ni siquiera username: allauth genera uno a partir
# del email). Si en el futuro se agrega "sede de preferencia" como campo de
# registro (mencionado como pendiente en delegacion_v2.md), un usuario que
# se registra por Google se lo va a saltear -- quedaría para completar
# después desde "Editar perfil", no se resuelve acá porque esa feature ni
# siquiera existe todavía.
SOCIALACCOUNT_AUTO_SIGNUP = True