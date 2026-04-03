from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Pago
from reservas.models import Reserva

try:
    from utils.email_utils import enviar_email_pago_confirmado
    EMAIL_DISPONIBLE = True
except ImportError:
    EMAIL_DISPONIBLE = False

try:
    from utils.qr_generator import generar_qr_imagen
    QR_DISPONIBLE = True
except ImportError:
    QR_DISPONIBLE = False
    print("⚠️ Módulo qrcode no encontrado. Instalar con: pip install qrcode[pil]")


@login_required
def procesar_pago(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    
    if reserva.cancelar_por_tiempo_expirado():
        messages.error(request, '⏰ Esta reserva fue cancelada automáticamente porque expiró el tiempo de pago (4 minutos). Los asientos han sido liberados.')
        return redirect('reservas:mis_reservas')
    
    if reserva.estado != 'pendiente':
        messages.error(request, 'Esta reserva no está pendiente de pago.')
        return redirect('reservas:mis_reservas')
    
    if hasattr(reserva, 'pago'):
        messages.error(request, 'Esta reserva ya tiene un pago registrado.')
        return redirect('reservas:detalle_reserva', reserva_id=reserva.id)
    
    if request.method == 'POST':
        if reserva.expiro_tiempo_pago():
            reserva.estado = 'cancelada'
            reserva.save()
            messages.error(request, '⏰ Lo sentimos, el tiempo de pago expiró mientras procesabas la transacción. Por favor, creá una nueva reserva.')
            return redirect('salas:lista_funciones')
        
        metodo_pago = request.POST.get('metodo_pago')
        
        # Crear el pago
        pago = Pago.objects.create(
            reserva=reserva,
            metodo_pago=metodo_pago,
            monto=reserva.total(),
            estado='aprobado'
        )
        
        if metodo_pago in ['tarjeta_debito', 'tarjeta_credito']:
            numero_tarjeta = request.POST.get('numero_tarjeta', '')
            if len(numero_tarjeta) >= 4:
                pago.ultimos_4_digitos = numero_tarjeta[-4:]
            pago.nombre_titular = request.POST.get('nombre_titular', '')
            pago.save()
        
        # Cambiar estado de la reserva a confirmada
        reserva.estado = 'confirmada'
        reserva.save()
        
        # NUEVO: Generar código QR automáticamente
        pago.generar_codigo_qr()
        pago.save()
        
        if EMAIL_DISPONIBLE:
            try:
                enviar_email_pago_confirmado(pago, request)
                messages.success(request, f'✅ ¡Pago procesado exitosamente! Número de transacción: {pago.numero_transaccion}. Te enviamos un email con el comprobante y código QR.')
            except Exception as e:
                messages.success(request, f'✅ ¡Pago procesado exitosamente! Número de transacción: {pago.numero_transaccion}')
                messages.warning(request, 'No pudimos enviar el email, pero tu pago está confirmado.')
        else:
            messages.success(request, f'✅ ¡Pago procesado exitosamente! Número de transacción: {pago.numero_transaccion}')
        
        return redirect('pagos:comprobante_pago', pago_id=pago.id)
    
    contexto = {
        'reserva': reserva,
        'total': reserva.total(),
    }
    return render(request, 'pagos/procesar_pago.html', contexto)


@login_required
def comprobante_pago(request, pago_id):
    pago = get_object_or_404(Pago, id=pago_id, reserva__usuario=request.user)
    
    # Generar imagen QR si está disponible la librería
    qr_imagen = None
    if QR_DISPONIBLE and pago.codigo_qr:
        try:
            qr_imagen = generar_qr_imagen(pago.codigo_qr)
        except Exception as e:
            print(f"Error generando QR: {e}")
    
    contexto = {
        'pago': pago,
        'reserva': pago.reserva,
        'qr_imagen': qr_imagen,
    }
    return render(request, 'pagos/comprobante_pago.html', contexto)


# ============================================
# NUEVAS VISTAS PARA VERIFICACIÓN DE QR
# ============================================

@login_required
def verificador_qr(request):
    """
    Vista para que el personal del cine escanee y verifique QR codes.
    Solo accesible para staff.
    """
    if not request.user.is_staff:
        messages.error(request, 'No tenés permisos para acceder a esta sección.')
        return redirect('peliculas:inicio')
    
    contexto = {}
    return render(request, 'pagos/verificador_qr.html', contexto)


@csrf_exempt  # Permitir POST desde scanner
def verificar_qr_api(request):
    """
    API para verificar un código QR.
    Retorna JSON con el estado del código.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    codigo_qr = request.POST.get('codigo_qr', '').strip()
    
    if not codigo_qr:
        return JsonResponse({
            'success': False,
            'error': 'Código QR vacío'
        })
    
    # Buscar el pago por código QR
    try:
        pago = Pago.objects.select_related(
            'reserva', 
            'reserva__usuario',
            'reserva__funcion',
            'reserva__funcion__pelicula',
            'reserva__funcion__sala'
        ).get(codigo_qr=codigo_qr)
    except Pago.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Código QR no encontrado',
            'valido': False
        })
    
    # Verificar si puede escanearse
    puede_escanear, mensaje = pago.puede_escanearse()
    
    if not puede_escanear:
        return JsonResponse({
            'success': True,
            'valido': False,
            'error': mensaje,
            'ya_escaneado': pago.qr_escaneado,
            'fecha_escaneo': pago.fecha_escaneo.isoformat() if pago.fecha_escaneo else None
        })
    
    # Retornar información de la reserva
    return JsonResponse({
        'success': True,
        'valido': True,
        'mensaje': 'QR válido - Listo para escanear',
        'reserva': {
            'codigo': pago.reserva.codigo_reserva,
            'pelicula': pago.reserva.funcion.pelicula.titulo,
            'sala': pago.reserva.funcion.sala.nombre,
            'fecha_hora': pago.reserva.funcion.fecha_hora.strftime('%d/%m/%Y %H:%M'),
            'cantidad_entradas': pago.reserva.cantidad_entradas,
            'asientos': pago.reserva.asientos_formateados() if pago.reserva.asientos_seleccionados else None,
            'usuario': pago.reserva.usuario.get_full_name() or pago.reserva.usuario.username,
            'total': str(pago.monto)
        }
    })


@csrf_exempt
def marcar_qr_escaneado(request):
    """
    API para marcar un QR como escaneado (usado).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    codigo_qr = request.POST.get('codigo_qr', '').strip()
    usuario = request.POST.get('usuario', 'Personal')
    
    if not codigo_qr:
        return JsonResponse({
            'success': False,
            'error': 'Código QR vacío'
        })
    
    try:
        pago = Pago.objects.get(codigo_qr=codigo_qr)
    except Pago.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Código QR no encontrado'
        })
    
    # Marcar como escaneado
    if pago.marcar_como_escaneado(usuario):
        return JsonResponse({
            'success': True,
            'mensaje': 'QR escaneado exitosamente',
            'fecha_escaneo': pago.fecha_escaneo.isoformat()
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'Este QR ya fue escaneado anteriormente',
            'fecha_escaneo': pago.fecha_escaneo.isoformat() if pago.fecha_escaneo else None
        })