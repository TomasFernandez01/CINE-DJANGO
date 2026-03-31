from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import Reserva
from salas.models import Funcion
from django.http import JsonResponse

# IMPORTAR LA FUNCIÓN DE EMAIL
try:
    from utils.email_utils import enviar_email_confirmacion_reserva, enviar_email_cancelacion_reserva
    EMAIL_DISPONIBLE = True
except ImportError:
    # Si no existe el módulo, funcionará sin emails
    EMAIL_DISPONIBLE = False
    print("⚠️ Módulo de emails no encontrado. Las notificaciones por email están deshabilitadas.")

#################################################################################
# ============================================
# NUEVA VISTA: Selección de Asientos
# ============================================
 
@login_required
def seleccionar_asientos(request, funcion_id):
    """
    Vista para seleccionar asientos específicos antes de crear la reserva.
    """
    funcion = get_object_or_404(Funcion, id=funcion_id)
    
    # Validar que la función esté disponible
    if funcion.fecha_hora <= timezone.now():
        messages.error(request, 'No se puede reservar esta función porque ya pasó.')
        return redirect('salas:lista_funciones')
    
    if not funcion.disponible:
        messages.error(request, 'Esta función no está disponible.')
        return redirect('salas:lista_funciones')
    
    # Obtener asientos ocupados
    asientos_ocupados = funcion.asientos_ocupados()
    
    # Obtener layout de la sala
    layout = funcion.sala.layout_asientos()
    
    contexto = {
        'funcion': funcion,
        'sala': funcion.sala,
        'layout': layout,
        'asientos_ocupados': asientos_ocupados,
        'asientos_disponibles': funcion.asientos_disponibles(),
    }
    
    return render(request, 'reservas/seleccionar_asientos.html', contexto)
 
 
@login_required
def confirmar_reserva_con_asientos(request, funcion_id):
    """
    Procesa la reserva con los asientos seleccionados.
    """
    if request.method != 'POST':
        return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)
    
    funcion = get_object_or_404(Funcion, id=funcion_id)
    
    # Obtener asientos seleccionados del POST
    asientos_seleccionados = request.POST.get('asientos_seleccionados', '')
    
    if not asientos_seleccionados:
        messages.error(request, 'Debes seleccionar al menos un asiento.')
        return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)
    
    # Convertir a lista
    asientos_lista = asientos_seleccionados.split(',')
    cantidad = len(asientos_lista)
    
    # VALIDACIÓN: Verificar que los asientos estén disponibles
    asientos_ocupados = funcion.asientos_ocupados()
    
    for asiento in asientos_lista:
        if asiento in asientos_ocupados:
            messages.error(request, f'El asiento {asiento} ya no está disponible. Por favor, seleccioná otros asientos.')
            return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)
    
    # VALIDACIÓN: Límite de entradas (1-10)
    if cantidad < 1 or cantidad > 4:
        messages.error(request, 'Debes seleccionar entre 1 y 4 asientos.')
        return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)
    
    # Crear la reserva con los asientos seleccionados
    reserva = Reserva.objects.create(
        usuario=request.user,
        funcion=funcion,
        cantidad_entradas=cantidad,
        asientos_seleccionados=asientos_seleccionados
    )
    
    # Enviar email si está disponible
    if EMAIL_DISPONIBLE:
        try:
            enviar_email_confirmacion_reserva(reserva, request)
            messages.success(
                request, 
                f'✅ Reserva creada exitosamente. Asientos: {reserva.asientos_formateados()}. '
                f'Código: {reserva.codigo_reserva}. Tenés 4 minutos para completar el pago.'
            )
        except Exception:
            messages.success(
                request,
                f'✅ Reserva creada exitosamente. Asientos: {reserva.asientos_formateados()}. '
                f'Código: {reserva.codigo_reserva}. Tenés 4 minutos para completar el pago.'
            )
    else:
        messages.success(
            request,
            f'✅ Reserva creada exitosamente. Asientos: {reserva.asientos_formateados()}. '
            f'Código: {reserva.codigo_reserva}. Tenés 4 minutos para completar el pago.'
        )
    
    return redirect('reservas:detalle_reserva', reserva_id=reserva.id)
 
 
@login_required
def verificar_asientos_disponibles(request, funcion_id):
    """
    API endpoint para verificar en tiempo real qué asientos están disponibles. Retorna JSON con lista de asientos ocupados.
    """
    funcion = get_object_or_404(Funcion, id=funcion_id)
    asientos_ocupados = funcion.asientos_ocupados()
    
    return JsonResponse({
        'success': True,
        'asientos_ocupados': asientos_ocupados,
        'total_disponibles': funcion.asientos_disponibles()
    })
#################################################################################

@login_required
def crear_reserva(request, funcion_id):
    # funcion = get_object_or_404(Funcion, id=funcion_id)
    
    # # VALIDACIÓN 1: Verificar que la función no haya pasado
    # if funcion.fecha_hora <= timezone.now():
    #     messages.error(request, 'No se puede reservar esta función porque ya pasó.')
    #     return redirect('salas:lista_funciones')
    
    # # VALIDACIÓN 2: Verificar que la función esté disponible
    # if not funcion.disponible:
    #     messages.error(request, 'Esta función no está disponible.')
    #     return redirect('salas:lista_funciones')
    
    # if request.method == 'POST':
    #     cantidad = int(request.POST.get('cantidad_entradas', 1))
        
    #     # VALIDACIÓN 3: Verificar límite de entradas (1-10)
    #     if cantidad < 1 or cantidad > 4:
    #         messages.error(request, 'Debes reservar entre 1 y 4 entradas.')
    #         return redirect('reservas:crear_reserva', funcion_id=funcion.id)
        
    #     # VALIDACIÓN 4: Verificar que hay asientos disponibles
    #     asientos_disponibles = funcion.asientos_disponibles()
    #     if cantidad > asientos_disponibles:
    #         messages.error(request, f'Solo hay {asientos_disponibles} asientos disponibles.')
    #         return redirect('reservas:crear_reserva', funcion_id=funcion.id)
        
    #     # Crear la reserva
    #     # NUEVO : (fecha_limite_pago se establece automáticamente en el modelo)
    #     reserva = Reserva.objects.create(
    #         usuario=request.user,
    #         funcion=funcion,
    #         cantidad_entradas=cantidad
    #     )
        
    #     # ENVIAR EMAIL DE CONFIRMACIÓN
    #     if EMAIL_DISPONIBLE:
    #         try:
    #             enviar_email_confirmacion_reserva(reserva, request)
    #             #messages.success(request, f'✅ Reserva creada exitosamente. Código: {reserva.codigo_reserva}. Te enviamos un email de confirmación.')
    #             messages.success(request, f'✅ Reserva creada exitosamente. Código: {reserva.codigo_reserva}. Tenés 4 minutos para completar el pago.')
    #         except Exception as e:
    #             # messages.success(request, f'✅ Reserva creada exitosamente. Código: {reserva.codigo_reserva}')
    #             # messages.warning(request, 'No pudimos enviar el email de confirmación, pero tu reserva está activa.')
    #             messages.success(request, f'✅ Reserva creada exitosamente. Código: {reserva.codigo_reserva}. Tenés 4 minutos para completar el pago.')
    #             messages.warning(request, 'No pudimos enviar el email de confirmación, pero tu reserva está activa.')
    #     else:
    #         messages.success(request, f'✅ Reserva creada exitosamente. Código: {reserva.codigo_reserva}')
    #         messages.success(request, f'✅ Reserva creada exitosamente. Código: {reserva.codigo_reserva}. Tenés 4 minutos para completar el pago.')
        
    #     return redirect('reservas:detalle_reserva', reserva_id=reserva.id)
    
    # contexto = {
    #     'funcion': funcion,
    #     'asientos_disponibles': funcion.asientos_disponibles(),
    # }
    # return render(request, 'reservas/crear_reserva.html', contexto)
    """
    Vista antigua - ahora redirige a selección de asientos.
    Mantener para compatibilidad con URLs antiguas.
    """
    # Redirigir a la nueva vista de selección de asientos
    return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)

@login_required
def mis_reservas(request):
    # Filtros
    # mostrar_canceladas = request.GET.get('mostrar_canceladas', 'si')
    # mostrar_expiradas = request.GET.get('mostrar_expiradas', 'si')
    
    # FILTROS CORREGIDOS: Si el checkbox NO está marcado, no viene en request.GET
    # Por defecto, mostrar todo (si=canceladas, si=expiradas)
    mostrar_canceladas = request.GET.get('mostrar_canceladas', 'si')
    mostrar_expiradas = request.GET.get('mostrar_expiradas', 'si')
    
    # Si el parámetro NO viene en la URL, significa que el checkbox está desmarcado
    # En ese caso, cambiamos a 'no'
    if 'mostrar_canceladas' not in request.GET and request.GET:
        mostrar_canceladas = 'no'
    if 'mostrar_expiradas' not in request.GET and request.GET:
        mostrar_expiradas = 'no'


    # Obtener todas las reservas del usuario
    reservas = Reserva.objects.filter(usuario=request.user).select_related('funcion__pelicula', 'funcion__sala')
    
    # NUEVO: Auto-cancelar reservas que expiraron por tiempo
    canceladas_tiempo = 0
    for reserva in reservas:
        if reserva.cancelar_por_tiempo_expirado():
            canceladas_tiempo += 1
    
    if canceladas_tiempo > 0:
        messages.warning(request, f'⏰ {canceladas_tiempo} reserva(s) cancelada(s) automáticamente por expiración del tiempo de pago.')

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
    
    # NUEVO: Verificar si expiró el tiempo de pago
    if reserva.cancelar_por_tiempo_expirado():
        messages.warning(request, '⏰ Esta reserva fue cancelada automáticamente porque expiró el tiempo de pago (4 minutos).')

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

    # NUEVO: Verificar tiempo de pago primero
    reserva.cancelar_por_tiempo_expirado()

    # Auto-expirar si corresponde
    reserva.actualizar_estado_si_expiro()
    
    # VALIDACIÓN 5: Verificar que se pueda cancelar (al menos 2 horas antes)
    # if not reserva.funcion.puede_cancelarse():
    #     messages.error(request, 'No se puede cancelar esta reserva. Debe hacerlo al menos 2 horas antes de la función.')
    #     return redirect('reservas:mis_reservas')
    
    # ============================================
    # FIX APLICADO: Solo validar 2 horas si está CONFIRMADA (pagada)
    # ============================================
    if reserva.estado == 'confirmada' and not reserva.funcion.puede_cancelarse():
        messages.error(request, 'No se puede cancelar esta reserva pagada. Debe hacerlo al menos 2 horas antes de la función.')
        return redirect('reservas:mis_reservas')
    
    # Permitir cancelar si es PENDIENTE (no pagada) en cualquier momento
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