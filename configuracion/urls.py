from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

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