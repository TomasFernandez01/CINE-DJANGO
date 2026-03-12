from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from reservas.models import Reserva
from .models import Pago

@login_required
def procesar_pago(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    
    # Verificar que la reserva esté pendiente
    if reserva.estado != 'pendiente':
        messages.error(request, 'Esta reserva no está pendiente de pago.')
        return redirect('reservas:mis_reservas')
    
    # Verificar que no tenga un pago ya
    if hasattr(reserva, 'pago'):
        messages.error(request, 'Esta reserva ya tiene un pago registrado.')
        return redirect('reservas:mis_reservas')
    
    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')
        
        # Datos opcionales de tarjeta (simulado)
        ultimos_4 = None
        if metodo_pago in ['tarjeta_debito', 'tarjeta_credito']:
            numero_tarjeta = request.POST.get('numero_tarjeta', '')
            if numero_tarjeta:
                ultimos_4 = numero_tarjeta[-4:] if len(numero_tarjeta) >= 4 else None
        
        # Crear el pago (automáticamente actualiza la reserva a confirmada)
        pago = Pago.objects.create(
            reserva=reserva,
            metodo_pago=metodo_pago,
            monto=reserva.total(),
            estado='aprobado',
            ultimos_4_digitos=ultimos_4
        )
        
        messages.success(request, f'¡Pago procesado exitosamente! Número de transacción: {pago.numero_transaccion}')
        return redirect('pagos:comprobante_pago', pago_id=pago.id)
    
    contexto = {
        'reserva': reserva,
    }
    return render(request, 'pagos/procesar_pago.html', contexto)

@login_required
def comprobante_pago(request, pago_id):
    pago = get_object_or_404(Pago, id=pago_id, reserva__usuario=request.user)
    
    contexto = {
        'pago': pago,
    }
    return render(request, 'pagos/comprobante_pago.html', contexto)