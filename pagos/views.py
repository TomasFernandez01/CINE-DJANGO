from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Pago
from reservas.models import Reserva

# IMPORTAR LA FUNCIÓN DE EMAIL
try:
    from utils.email_utils import enviar_email_pago_confirmado
    EMAIL_DISPONIBLE = True
except ImportError:
    EMAIL_DISPONIBLE = False
    print("⚠️ Módulo de emails no encontrado. Las notificaciones por email están deshabilitadas.")

@login_required
def procesar_pago(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    
    # NUEVO: Verificar si expiró el tiempo de pago
    if reserva.cancelar_por_tiempo_expirado():
        messages.error(request, '⏰ Esta reserva fue cancelada automáticamente porque expiró el tiempo de pago (4 minutos). Los asientos han sido liberados.')
        return redirect('reservas:mis_reservas')

    # Verificar que la reserva esté pendiente
    if reserva.estado != 'pendiente':
        messages.error(request, 'Esta reserva no está pendiente de pago.')
        return redirect('reservas:mis_reservas')
    
    # Verificar que no tenga ya un pago
    if hasattr(reserva, 'pago'):
        messages.error(request, 'Esta reserva ya tiene un pago registrado.')
        return redirect('reservas:detalle_reserva', reserva_id=reserva.id)
    
    if request.method == 'POST':

        # DOBLE VERIFICACIÓN antes de procesar el pago
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
        
        # Si es tarjeta, guardar últimos 4 dígitos (simulado)
        if metodo_pago in ['tarjeta_debito', 'tarjeta_credito']:
            numero_tarjeta = request.POST.get('numero_tarjeta', '')
            if len(numero_tarjeta) >= 4:
                pago.ultimos_4_digitos = numero_tarjeta[-4:]
            pago.nombre_titular = request.POST.get('nombre_titular', '')
            pago.save()
        
        # Cambiar estado de la reserva a confirmada
        reserva.estado = 'confirmada'
        reserva.save()
        
        # ENVIAR EMAIL DE CONFIRMACIÓN DE PAGO
        if EMAIL_DISPONIBLE:
            try:
                enviar_email_pago_confirmado(pago, request)
                messages.success(request, f'✅ ¡Pago procesado exitosamente! Número de transacción: {pago.numero_transaccion}. Te enviamos un email con el comprobante.')
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
    
    contexto = {
        'pago': pago,
        'reserva': pago.reserva,
    }
    return render(request, 'pagos/comprobante_pago.html', contexto)