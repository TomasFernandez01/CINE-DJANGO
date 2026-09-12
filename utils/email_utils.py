# utils/email_utils.py
# Crear este archivo en una carpeta utils/ en la raíz del proyecto
# O dentro de cualquier app (por ejemplo, en reservas/email_utils.py)

from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.conf import settings
# nuevo (restyle - QR, corregido a CID): base64 para decodificar lo que
# devuelve generar_qr_imagen(), MIMEImage para adjuntar el QR como imagen
# inline con Content-ID (ver enviar_email_pago_confirmado más abajo).
import base64
from email.mime.image import MIMEImage
import logging

logger = logging.getLogger(__name__)

# nuevo (restyle - QR en pago confirmado): mismo patrón de import guardado
# que ya usa pagos/views.py -- si el paquete qrcode no está instalado, el
# resto del sitio sigue andando (no se rompe nada), simplemente el mail de
# pago confirmado sale sin la sección de QR (ver `qr_imagen` más abajo).
try:
    from utils.qr_generator import generar_qr_imagen
    QR_DISPONIBLE = True
except ImportError:
    QR_DISPONIBLE = False
    logger.warning("Módulo qrcode no encontrado. Instalar con: pip install qrcode[pil]")


# modificado (Hilo 1 - ronda "producción"): aviso sobre el límite de envío
# de Gmail, pedido explícitamente en delegacion_v3.md.
#
# Una cuenta de Gmail normal (no Google Workspace) tiene un límite de
# ~500 emails salientes por día vía SMTP (500/día para cuentas @gmail.com,
# 2000/día para Workspace). Si se supera, Gmail empieza a rechazar el
# envío (típicamente un error 454/550 de smtplib). Ese error ya queda
# contenido: cada función de este archivo tiene su propio try/except y
# devuelve False en vez de propagar la excepción (ver más abajo), así que
# un pico de envíos NUNCA rompe el flujo de compra del usuario -- la
# reserva/pago se confirma igual, el usuario simplemente no recibe ese
# mail puntual.
#
# Lo que este comentario NO resuelve (documentado para cuando el volumen
# crezca, fuera del alcance de este hilo): como el fallo se traga
# silenciosamente, si un día se pisa el límite de Gmail nadie se entera
# salvo revisando los logs (logger.error de cada función de abajo). Si el
# volumen de reservas crece y se acerca a ese límite, las dos salidas son
# (a) pasar la cuenta a Google Workspace (sube el límite a 2000/día) o
# (b) migrar a un servicio pensado para volumen transaccional (Mailgun,
# SendGrid, Amazon SES, etc.), que además evita que Gmail marque la cuenta
# como spam por enviar de forma automatizada.


# modificado (Hilo 1 - Tanda D): antes esto usaba directo settings.DEFAULT_FROM_EMAIL
# y la conexión default de Django (que lee EMAIL_BACKEND/EMAIL_HOST/etc de
# settings.py). Ahora se prioriza lo que esté cargado en Panel > Configuración
# General > Envío de emails; si no hay nada cargado o está en modo "consola",
# se comporta exactamente igual que antes (conexión default de settings.py).
def _config_email(sede=None):
    # modificado (T11): parámetro opcional `sede` para que, si esa sede tiene
    # su propia fila de ConfiguracionGeneral (T9) con su propio servidor de
    # email, se use esa en vez de siempre la global. Sin argumento (o sin fila
    # propia de esa sede), se comporta exactamente igual que antes.
    try:
        from panel.models import ConfiguracionGeneral
        return ConfiguracionGeneral.obtener(sede=sede)
    except Exception:
        return None


def _obtener_conexion(sede=None):
    config = _config_email(sede=sede)
    if not config or config.email_backend != 'smtp' or not config.email_host:
        return None  # None -> Django usa la conexión default de settings.py
    return get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=config.email_host,
        port=config.email_port or 587,
        username=config.email_host_user or None,
        password=config.email_host_password or None,
        use_tls=config.email_use_tls,
    )


def _obtener_from_email(sede=None):
    config = _config_email(sede=sede)
    if config and config.email_from:
        return config.email_from
    return getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost')


def _sede_de(reserva):
    # nuevo (T11 / Hilo 2 punto 2): helper compartido para sacar la sede de
    # una reserva de forma segura (nunca rompe el envío del email si por
    # algún motivo faltara el dato).
    try:
        return reserva.funcion.sala.sede
    except Exception:
        return None


def enviar_email_confirmacion_reserva(reserva, request=None):
    """
    Envía email de confirmación cuando se crea una reserva
    """
    # modificado: se sacaron los print("🔍 DEBUG: ...") que quedaron de una sesión de
    # debugging (comentario "# ← AGREGAR" delataba que eran temporales). El logger.info/
    # logger.error de abajo ya cubre el mismo registro, sin ensuciar la consola en producción.
    try:
        usuario = reserva.usuario
        sede = _sede_de(reserva)  # modificado (T11 / Hilo 2 punto 2)
        subject = f'🎬 Reserva Confirmada - {reserva.codigo_reserva}'

        # Obtener el dominio del sitio
        if request:
            domain = request.build_absolute_uri('/').rstrip('/')
        else:
            domain = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'

        # Renderizar el template HTML
        # modificado (T11 / Hilo 2 punto 2): se agrega `sede` al contexto para
        # mostrarla en el email (nombre y dirección), no solo el nombre de sala.
        html_content = render_to_string('emails/reserva_confirmada.html', {
            'usuario': usuario,
            'reserva': reserva,
            'domain': domain,
            'sede': sede,
        })

        # Crear el email
        email = EmailMultiAlternatives(
            subject=subject,
            body=f'Tu reserva {reserva.codigo_reserva} ha sido confirmada...',
            from_email=_obtener_from_email(sede=sede),
            to=[usuario.email],
            connection=_obtener_conexion(sede=sede)
        )
        email.attach_alternative(html_content, "text/html")

        # Enviar
        email.send()

        logger.info(f'Email de confirmación enviado a {usuario.email}')
        return True

    except Exception as e:
        logger.error(f'Error enviando email de confirmación: {str(e)}')
        return False


def enviar_email_pago_confirmado(pago, request=None):
    """
    Envía email de confirmación cuando se procesa un pago
    """
    try:
        reserva = pago.reserva
        usuario = reserva.usuario
        sede = _sede_de(reserva)  # modificado (T11 / Hilo 2 punto 2)
        subject = f'✅ Pago Confirmado - {pago.numero_transaccion}'
        
        # Obtener el dominio del sitio
        if request:
            domain = request.build_absolute_uri('/').rstrip('/')
        else:
            domain = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'
        
        # nuevo (restyle - QR en pago confirmado): mismo generar_qr_imagen()
        # que ya usa pagos/views.py para el ticket del sitio -- mismo dato
        # (pago.codigo_qr), no se inventa nada nuevo.
        #
        # corregido: la primera versión pasaba esto como base64 inline
        # (`<img src="data:image/png;base64,...">`), que funciona bien
        # dentro del sitio pero NO en Gmail -- es una limitación conocida
        # y documentada de Gmail (no soporta imágenes data-URI en el
        # cuerpo del mail, a diferencia de lo que se asumió al principio).
        # La forma correcta es adjuntar la imagen como "inline" con un
        # Content-ID y referenciarla desde el HTML como `cid:qr_reserva`
        # -- eso sí lo soportan Gmail, Outlook y prácticamente todos los
        # clientes. Por eso acá se decodifica el base64 que ya devuelve
        # generar_qr_imagen() a bytes crudos, en vez de tocar
        # utils/qr_generator.py (que lo siguen usando tal cual otras
        # partes del sitio para mostrar el QR en una página web, donde
        # base64 sí funciona sin problema).
        qr_bytes = None
        if QR_DISPONIBLE and getattr(pago, 'codigo_qr', None):
            try:
                qr_data_uri = generar_qr_imagen(pago.codigo_qr)
                _, qr_b64 = qr_data_uri.split(',', 1)
                qr_bytes = base64.b64decode(qr_b64)
            except Exception as e:
                logger.warning(f'No se pudo generar el QR para el email de pago {pago.numero_transaccion}: {e}')

        # Renderizar el template HTML
        # modificado (T11 / Hilo 2 punto 2): se agrega `sede` al contexto.
        # modificado (restyle - QR, corregido a CID): el template ya no
        # recibe la imagen en sí, solo un booleano -- el `src="cid:..."`
        # está fijo en el template, la imagen se adjunta más abajo.
        html_content = render_to_string('emails/pago_confirmado.html', {
            'usuario': usuario,
            'reserva': reserva,
            'pago': pago,
            'domain': domain,
            'sede': sede,
            'qr_disponible': qr_bytes is not None,
        })
        
        # Texto plano como alternativa
        # modificado (T11 / Hilo 2 punto 2): se agrega la sede al texto plano.
        text_content = f"""
        ¡Pago Exitoso!
        
        Hola {usuario.first_name or usuario.username},
        
        Tu pago se procesó correctamente.
        
        Número de transacción: {pago.numero_transaccion}
        Monto: ${pago.monto}
        
        Película: {reserva.funcion.pelicula.titulo}
        Sede: {sede.nombre if sede else '-'}
        Código de reserva: {reserva.codigo_reserva}
        Fecha: {reserva.funcion.fecha_hora.strftime('%d/%m/%Y')}
        Horario: {reserva.funcion.fecha_hora.strftime('%H:%M')} hs
        
        ¡Te esperamos en el cine!
        """
        
        # Crear el email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=_obtener_from_email(sede=sede),
            to=[usuario.email],
            connection=_obtener_conexion(sede=sede)
        )
        email.attach_alternative(html_content, "text/html")

        # nuevo (restyle - QR, corregido a CID): mixed_subtype = 'related'
        # es necesario para que Gmail/Outlook traten la imagen como
        # "inline" (mostrada en el cuerpo) en vez de como un archivo
        # adjunto aparte -- sin esto, aunque se adjunte con Content-ID,
        # algunos clientes la muestran como adjunto suelto al final.
        if qr_bytes:
            email.mixed_subtype = 'related'
            qr_mime = MIMEImage(qr_bytes, _subtype='png')
            qr_mime.add_header('Content-ID', '<qr_reserva>')
            qr_mime.add_header('Content-Disposition', 'inline', filename='qr.png')
            email.attach(qr_mime)
        
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
        sede = _sede_de(reserva)  # modificado (T11 / Hilo 2 punto 2)
        subject = f'🔔 Recordatorio: Tu función es mañana - {reserva.funcion.pelicula.titulo}'
        
        # Obtener el dominio del sitio
        if request:
            domain = request.build_absolute_uri('/').rstrip('/')
        else:
            domain = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'
        
        # Renderizar el template HTML
        # modificado (T11 / Hilo 2 punto 2): se agrega `sede` al contexto.
        html_content = render_to_string('emails/recordatorio.html', {
            'usuario': usuario,
            'reserva': reserva,
            'domain': domain,
            'sede': sede,
        })
        
        # Texto plano como alternativa
        # modificado (T11 / Hilo 2 punto 2): se agrega la sede (además de la
        # sala, que ya estaba) al texto plano.
        text_content = f"""
        ¡No te lo pierdas!
        
        Hola {usuario.first_name or usuario.username},
        
        Te recordamos que tu función es MAÑANA:
        
        Película: {reserva.funcion.pelicula.titulo}
        Sede: {sede.nombre if sede else '-'}
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
            from_email=_obtener_from_email(sede=sede),
            to=[usuario.email],
            connection=_obtener_conexion(sede=sede)
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
        sede = _sede_de(reserva)  # modificado (T11 / Hilo 2 punto 2)
        subject = f'Reserva Cancelada - {reserva.codigo_reserva}'
        
        # modificado (T11 / Hilo 2 punto 2): se agrega la sede al texto plano.
        text_content = f"""
        Reserva Cancelada
        
        Hola {usuario.first_name or usuario.username},
        
        Tu reserva ha sido cancelada:
        
        Código: {reserva.codigo_reserva}
        Película: {reserva.funcion.pelicula.titulo}
        Sede: {sede.nombre if sede else '-'}
        Fecha: {reserva.funcion.fecha_hora.strftime('%d/%m/%Y %H:%M')}
        
        Si cancelaste por error, podés crear una nueva reserva desde nuestra web.
        
        Saludos,
        Cine Online
        """
        
        # Crear el email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=_obtener_from_email(sede=sede),
            to=[usuario.email],
            connection=_obtener_conexion(sede=sede)
        )
        
        # Enviar
        email.send()
        logger.info(f'Email de cancelación enviado a {usuario.email} para reserva {reserva.codigo_reserva}')
        return True
        
    except Exception as e:
        logger.error(f'Error enviando email de cancelación: {str(e)}')
        return False