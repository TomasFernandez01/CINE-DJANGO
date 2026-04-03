# utils/qr_generator.py
# Crear en: utils/qr_generator.py

import qrcode
from io import BytesIO
import base64
from django.conf import settings

def generar_qr_imagen(codigo, size=300):
    """
    Genera una imagen QR a partir de un código.
    Retorna la imagen como base64 para usar en HTML.
    
    Args:
        codigo (str): El código a convertir en QR
        size (int): Tamaño de la imagen en píxeles
    
    Returns:
        str: Imagen en formato base64 (data:image/png;base64,...)
    """
    # Configurar el generador QR
    qr = qrcode.QRCode(
        version=1,  # Tamaño del QR (1 es el más pequeño)
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # Alta corrección de errores
        box_size=10,  # Tamaño de cada "caja" del QR
        border=4,  # Borde alrededor del QR
    )
    
    # Agregar datos
    qr.add_data(codigo)
    qr.make(fit=True)
    
    # Crear la imagen
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a BytesIO
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Convertir a base64
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}"


def generar_qr_archivo(codigo, filepath):
    """
    Genera una imagen QR y la guarda en un archivo.
    
    Args:
        codigo (str): El código a convertir en QR
        filepath (str): Ruta donde guardar el archivo
    
    Returns:
        str: Ruta del archivo guardado
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    
    qr.add_data(codigo)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filepath)
    
    return filepath


def verificar_qr_valido(codigo):
    """
    Verifica si un código QR es válido para nuestro sistema.
    Debe tener el formato: CINE-{UUID}-{CODIGO_RESERVA}
    
    Args:
        codigo (str): Código a verificar
    
    Returns:
        tuple: (bool, str) - (Es válido, Mensaje)
    """
    if not codigo:
        return False, "Código vacío"
    
    partes = codigo.split('-')
    
    if len(partes) != 3:
        return False, "Formato de código inválido"
    
    if partes[0] != 'CINE':
        return False, "Código no pertenece a este sistema"
    
    if len(partes[1]) != 8:
        return False, "UUID inválido"
    
    if len(partes[2]) != 10:
        return False, "Código de reserva inválido"
    
    return True, "Código válido"


def extraer_codigo_reserva(codigo_qr):
    """
    Extrae el código de reserva desde un código QR.
    
    Args:
        codigo_qr (str): Código QR completo (CINE-UUID-CODIGO)
    
    Returns:
        str: Código de reserva o None
    """
    try:
        partes = codigo_qr.split('-')
        if len(partes) == 3:
            return partes[2]
    except:
        pass
    return None