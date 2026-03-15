# utils/email_utils.py
# Crear este archivo en una carpeta utils/ en la raíz del proyecto
# O dentro de cualquier app (por ejemplo, en reservas/email_utils.py)

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def enviar_email_confirmacion_reserva(reserva, request=None):
    """
    Envía email de confirmación cuando se crea una reserva
    """
    print("🔍 DEBUG: Intentando enviar email de confirmación...")  # ← AGREGAR
    
    try:
        usuario = reserva.usuario
        subject = f'🎬 Reserva Confirmada - {reserva.codigo_reserva}'
        
        print(f"🔍 DEBUG: Email destino: {usuario.email}")  # ← AGREGAR
        print(f"🔍 DEBUG: Subject: {subject}")  # ← AGREGAR
        
        # Obtener el dominio del sitio
        if request:
            domain = request.build_absolute_uri('/').rstrip('/')
        else:
            domain = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'
        
        print(f"🔍 DEBUG: Domain: {domain}")  # ← AGREGAR
        
        # Renderizar el template HTML
        print("🔍 DEBUG: Intentando renderizar template...")  # ← AGREGAR
        html_content = render_to_string('emails/reserva_confirmada.html', {
            'usuario': usuario,
            'reserva': reserva,
            'domain': domain,
        })
        print("🔍 DEBUG: Template renderizado OK")  # ← AGREGAR
        
        # Crear el email
        email = EmailMultiAlternatives(
            subject=subject,
            body=f'Tu reserva {reserva.codigo_reserva} ha sido confirmada...',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[usuario.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Enviar
        print("🔍 DEBUG: Intentando enviar email...")  # ← AGREGAR
        email.send()
        print("🔍 DEBUG: Email enviado exitosamente!")  # ← AGREGAR
        
        logger.info(f'Email de confirmación enviado a {usuario.email}')
        return True
        
    except Exception as e:
        print(f"❌ DEBUG ERROR: {str(e)}")  # ← AGREGAR
        logger.error(f'Error enviando email de confirmación: {str(e)}')
        return False


def enviar_email_pago_confirmado(pago, request=None):
    """
    Envía email de confirmación cuando se procesa un pago
    """
    try:
        reserva = pago.reserva
        usuario = reserva.usuario
        subject = f'✅ Pago Confirmado - {pago.numero_transaccion}'
        
        # Obtener el dominio del sitio
        if request:
            domain = request.build_absolute_uri('/').rstrip('/')
        else:
            domain = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'
        
        # Renderizar el template HTML
        html_content = render_to_string('emails/pago_confirmado.html', {
            'usuario': usuario,
            'reserva': reserva,
            'pago': pago,
            'domain': domain,
        })
        
        # Texto plano como alternativa
        text_content = f"""
        ¡Pago Exitoso!
        
        Hola {usuario.first_name or usuario.username},
        
        Tu pago se procesó correctamente.
        
        Número de transacción: {pago.numero_transaccion}
        Monto: ${pago.monto}
        
        Película: {reserva.funcion.pelicula.titulo}
        Código de reserva: {reserva.codigo_reserva}
        Fecha: {reserva.funcion.fecha_hora.strftime('%d/%m/%Y')}
        Horario: {reserva.funcion.fecha_hora.strftime('%H:%M')} hs
        
        ¡Te esperamos en el cine!
        """
        
        # Crear el email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[usuario.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Enviar
        email.send()
        logger.info(f'Email de pago confirmado enviado a {usuario.email} para pago {pago.numero_transaccion}')
        return True
        
    except Exception as e:
        logger.error(f'Error enviando email de pago: {str(e)}')
        return False


def enviar_email_recordatorio_funcion(reserva, request=None):
    """
    Envía email recordatorio 24hs antes de la función
    """
    try:
        usuario = reserva.usuario
        subject = f'🔔 Recordatorio: Tu función es mañana - {reserva.funcion.pelicula.titulo}'
        
        # Obtener el dominio del sitio
        if request:
            domain = request.build_absolute_uri('/').rstrip('/')
        else:
            domain = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'
        
        # Renderizar el template HTML
        html_content = render_to_string('emails/recordatorio.html', {
            'usuario': usuario,
            'reserva': reserva,
            'domain': domain,
        })
        
        # Texto plano como alternativa
        text_content = f"""
        ¡No te lo pierdas!
        
        Hola {usuario.first_name or usuario.username},
        
        Te recordamos que tu función es MAÑANA:
        
        Película: {reserva.funcion.pelicula.titulo}
        Fecha: {reserva.funcion.fecha_hora.strftime('%d/%m/%Y')}
        Horario: {reserva.funcion.fecha_hora.strftime('%H:%M')} hs
        Sala: {reserva.funcion.sala.nombre}
        Código de reserva: {reserva.codigo_reserva}
        
        Llegá 15 minutos antes y presentá tu código en boletería.
        
        ¡Nos vemos en el cine!
        """
        
        # Crear el email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[usuario.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Enviar
        email.send()
        logger.info(f'Email recordatorio enviado a {usuario.email} para reserva {reserva.codigo_reserva}')
        return True
        
    except Exception as e:
        logger.error(f'Error enviando email recordatorio: {str(e)}')
        return False


def enviar_email_cancelacion_reserva(reserva):
    """
    Envía email cuando se cancela una reserva
    """
    try:
        usuario = reserva.usuario
        subject = f'Reserva Cancelada - {reserva.codigo_reserva}'
        
        text_content = f"""
        Reserva Cancelada
        
        Hola {usuario.first_name or usuario.username},
        
        Tu reserva ha sido cancelada:
        
        Código: {reserva.codigo_reserva}
        Película: {reserva.funcion.pelicula.titulo}
        Fecha: {reserva.funcion.fecha_hora.strftime('%d/%m/%Y %H:%M')}
        
        Si cancelaste por error, podés crear una nueva reserva desde nuestra web.
        
        Saludos,
        Cine Online
        """
        
        # Crear el email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[usuario.email]
        )
        
        # Enviar
        email.send()
        logger.info(f'Email de cancelación enviado a {usuario.email} para reserva {reserva.codigo_reserva}')
        return True
        
    except Exception as e:
        logger.error(f'Error enviando email de cancelación: {str(e)}')
        return False