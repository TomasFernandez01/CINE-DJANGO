from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import Reserva
from salas.models import Funcion

# IMPORTAR LA FUNCIÓN DE EMAIL
try:
    from utils.email_utils import enviar_email_confirmacion_reserva, enviar_email_cancelacion_reserva
    EMAIL_DISPONIBLE = True
except ImportError:
    # Si no existe el módulo, funcionará sin emails
    EMAIL_DISPONIBLE = False
    print("⚠️ Módulo de emails no encontrado. Las notificaciones por email están deshabilitadas.")

@login_required
def crear_reserva(request, funcion_id):
    funcion = get_object_or_404(Funcion, id=funcion_id)
    
    # VALIDACIÓN 1: Verificar que la función no haya pasado
    if funcion.fecha_hora <= timezone.now():
        messages.error(request, 'No se puede reservar esta función porque ya pasó.')
        return redirect('salas:lista_funciones')
    
    # VALIDACIÓN 2: Verificar que la función esté disponible
    if not funcion.disponible:
        messages.error(request, 'Esta función no está disponible.')
        return redirect('salas:lista_funciones')
    
    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad_entradas', 1))
        
        # VALIDACIÓN 3: Verificar límite de entradas (1-10)
        if cantidad < 1 or cantidad > 10:
            messages.error(request, 'Debes reservar entre 1 y 10 entradas.')
            return redirect('reservas:crear_reserva', funcion_id=funcion.id)
        
        # VALIDACIÓN 4: Verificar que hay asientos disponibles
        asientos_disponibles = funcion.asientos_disponibles()
        if cantidad > asientos_disponibles:
            messages.error(request, f'Solo hay {asientos_disponibles} asientos disponibles.')
            return redirect('reservas:crear_reserva', funcion_id=funcion.id)
        
        # Crear la reserva
        reserva = Reserva.objects.create(
            usuario=request.user,
            funcion=funcion,
            cantidad_entradas=cantidad
        )
        
        # ENVIAR EMAIL DE CONFIRMACIÓN
        if EMAIL_DISPONIBLE:
            try:
                enviar_email_confirmacion_reserva(reserva, request)
                messages.success(request, f'✅ Reserva creada exitosamente. Código: {reserva.codigo_reserva}. Te enviamos un email de confirmación.')
            except Exception as e:
                messages.success(request, f'✅ Reserva creada exitosamente. Código: {reserva.codigo_reserva}')
                messages.warning(request, 'No pudimos enviar el email de confirmación, pero tu reserva está activa.')
        else:
            messages.success(request, f'✅ Reserva creada exitosamente. Código: {reserva.codigo_reserva}')
        
        return redirect('reservas:detalle_reserva', reserva_id=reserva.id)
    
    contexto = {
        'funcion': funcion,
        'asientos_disponibles': funcion.asientos_disponibles(),
    }
    return render(request, 'reservas/crear_reserva.html', contexto)

@login_required
def mis_reservas(request):
    # Filtros
    mostrar_canceladas = request.GET.get('mostrar_canceladas', 'si')
    mostrar_expiradas = request.GET.get('mostrar_expiradas', 'si')
    
    # Obtener todas las reservas del usuario
    reservas = Reserva.objects.filter(usuario=request.user).select_related('funcion__pelicula', 'funcion__sala')
    
    # Auto-expirar reservas que ya pasaron
    expiradas_count = 0
    for reserva in reservas:
        if reserva.actualizar_estado_si_expiro():
            expiradas_count += 1
    
    if expiradas_count > 0:
        messages.info(request, f'{expiradas_count} reserva(s) expirada(s) automáticamente.')
    
    # Aplicar filtros
    if mostrar_canceladas == 'no':
        reservas = reservas.exclude(estado='cancelada')
    
    if mostrar_expiradas == 'no':
        reservas = reservas.exclude(estado='expirada')
    
    contexto = {
        'reservas': reservas,
        'mostrar_canceladas': mostrar_canceladas,
        'mostrar_expiradas': mostrar_expiradas,
    }
    return render(request, 'reservas/mis_reservas.html', contexto)

@login_required
def detalle_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    
    # Auto-expirar si corresponde
    if reserva.actualizar_estado_si_expiro():
        messages.info(request, 'Esta reserva ha expirado porque la función ya pasó.')
    
    contexto = {
        'reserva': reserva
    }
    return render(request, 'reservas/detalle_reserva.html', contexto)

@login_required
def cancelar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    
    # Auto-expirar si corresponde
    reserva.actualizar_estado_si_expiro()
    
    # VALIDACIÓN 5: Verificar que se pueda cancelar (al menos 2 horas antes)
    if not reserva.funcion.puede_cancelarse():
        messages.error(request, 'No se puede cancelar esta reserva. Debe hacerlo al menos 2 horas antes de la función.')
        return redirect('reservas:mis_reservas')
    
    if reserva.estado == 'pendiente':
        reserva.estado = 'cancelada'
        reserva.save()
        
        # ENVIAR EMAIL DE CANCELACIÓN
        if EMAIL_DISPONIBLE:
            try:
                enviar_email_cancelacion_reserva(reserva)
                messages.success(request, '✅ Reserva cancelada exitosamente. Te enviamos un email de confirmación.')
            except Exception as e:
                messages.success(request, '✅ Reserva cancelada exitosamente.')
        else:
            messages.success(request, '✅ Reserva cancelada exitosamente.')
    else:
        messages.error(request, 'No se puede cancelar esta reserva.')
    
    return redirect('reservas:mis_reservas')

@login_required
def eliminar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    
    # Permitir eliminar reservas canceladas O expiradas
    if reserva.estado in ['cancelada', 'expirada']:
        codigo = reserva.codigo_reserva
        reserva.delete()
        messages.success(request, f'Reserva {codigo} eliminada del historial.')
    else:
        messages.error(request, 'Solo se pueden eliminar reservas canceladas o expiradas.')
    
    return redirect('reservas:mis_reservas')