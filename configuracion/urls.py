from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('sedes.urls')),
    path('', include('peliculas.urls')),
    path('', include('salas.urls')),
    path('', include('reservas.urls')),
    path('', include('usuarios.urls')),
    path('', include('pagos.urls')),
    path('', include('promociones.urls')),
    path('panel/', include('panel.urls')),
    # modificado (Hilo 2 - última tarea, estilos de allauth): las urls
    # propias de allauth (/accounts/login/, /accounts/logout/) vienen sin
    # estilo y además duplican páginas que ya tenemos (usuarios:login,
    # usuarios:logout). En vez de mantener un segundo formulario de login
    # en paralelo, se redirige a quien llegue a esas 2 urls puntuales a
    # nuestras páginas reales. Van ANTES de include('allauth.urls') porque
    # Django resuelve la primera url que matchea -- el resto de allauth
    # (Google, pantallas de error, etc.) sigue funcionando igual, esto
    # solo intercepta esos 2 paths puntuales.
    # modificado (última tarea): mismo motivo que login/logout arriba, pero
    # más importante todavía -- /accounts/signup/ es el ALTA NATIVA de
    # allauth (allauth.account), totalmente separada de
    # usuarios/forms.py::RegistroForm. No pide nombre/apellido/teléfono y
    # el email es opcional (nuestro RegistroForm lo exige) -- dejarla
    # accesible permitía crear usuarios "incompletos" respecto al resto de
    # la app (por ejemplo, sin email, el adapter de Hilo 2 que vincula
    # cuentas de Google por email no tendría con qué vincular a ese User).
    # Se cierra ese camino paralelo, no solo se le pone estilo.
    path('accounts/signup/', RedirectView.as_view(pattern_name='usuarios:registro')),
    path('accounts/login/', RedirectView.as_view(pattern_name='usuarios:login', query_string=True)),
    path('accounts/logout/', RedirectView.as_view(pattern_name='usuarios:logout')),
    # modificado (Hilo 2 - Google Sign-In): urls propias de allauth (el
    # flujo de OAuth con Google vive bajo /accounts/...). No estaba en la
    # lista original de archivos permitidos del Hilo 2 -- se agregó con
    # autorización explícita, es imprescindible para que el botón de
    # Google funcione (allauth arma sus propias URLs, no se pueden definir
    # a mano sin reimplementar la librería).
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)