# nuevo (Hilo 2 - Google Sign-In): adapter custom de django-allauth.
#
# Objetivo único: si alguien inicia sesión con Google y ya existe un User de
# Django con ese mismo email (por ejemplo, se había registrado antes con
# usuario/contraseña vía RegistroForm), se vincula la cuenta de Google a ESE
# User existente en vez de que allauth tire un error de "ese email ya está
# en uso" o cree un usuario duplicado. Es exactamente el punto que pedía
# reportes/delegacion/delegacion_v3.md, Hilo 2:
# "Revisar que un usuario que ya se registró con contraseña pueda vincular
# su cuenta de Google después (mismo email) sin duplicar el usuario".
#
# Se resuelve con un adapter (en vez de settings tipo
# SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT) porque ese comportamiento
# cambió de nombre entre versiones de allauth -- pre_social_login() es la
# forma documentada y estable entre versiones para este caso de uso.

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        # Si esta SocialAccount ya está conectada a un User (no es la
        # primera vez que este Google entra), no hay nada que decidir.
        if sociallogin.is_existing:
            return

        email = sociallogin.account.extra_data.get('email')
        if not email:
            # Debería venir siempre (se pide 'email' en SCOPE, ver
            # settings.py), pero por las dudas no rompemos el login si por
            # algún motivo no vino.
            return

        from django.contrib.auth.models import User

        try:
            user_existente = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # No existe un User con ese email -> allauth sigue su flujo
            # normal (SOCIALACCOUNT_AUTO_SIGNUP crea uno nuevo).
            return
        except User.MultipleObjectsReturned:
            # nota (Hilo 2): el modelo User de Django (ni RegistroForm) no
            # fuerza email único a nivel de base de datos hoy -- en teoría
            # podría haber más de un User con el mismo email ya cargado
            # antes de este hilo. Si eso pasa, no adivinamos a cuál
            # conectar: dejamos que allauth siga su flujo normal (que va a
            # mostrar el error de "email en uso" de allauth) en vez de
            # vincular a ciegas a uno de los dos. Si esto se ve en la
            # práctica, la solución real es otra tanda que audite/corrija
            # emails duplicados, no algo para resolver acá.
            return

        # Conecta esta cuenta de Google al User existente encontrado por
        # email. A partir de acá, ese User puede loguearse tanto con su
        # contraseña original como con "Continuar con Google".
        sociallogin.connect(request, user_existente)
