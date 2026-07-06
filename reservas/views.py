from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta , datetime
from .models import Reserva
from salas.models import Funcion
from django.conf import settings

try:
    from utils.email_utils import enviar_email_confirmacion_reserva, enviar_email_cancelacion_reserva
    EMAIL_DISPONIBLE = True
except ImportError:
    EMAIL_DISPONIBLE = False

try:
    from utils.qr_generator import generar_qr_imagen
    QR_DISPONIBLE = True
except ImportError:
    QR_DISPONIBLE = False


def get_max_asientos():
    return getattr(settings, 'MAX_ASIENTOS_POR_RESERVA', 6)
 
 
def get_tiempo_limite():
    return getattr(settings, 'TIEMPO_LIMITE_PAGO_MINUTOS', 15)

# ============================================
# VISTAS DE SELECCIÓN DE ASIENTOS
# ============================================

@login_required
def seleccionar_asientos(request, funcion_id):
    """Vista para seleccionar asientos específicos antes de crear la reserva."""
    funcion = get_object_or_404(Funcion, id=funcion_id)
    
    if funcion.fecha_hora <= timezone.now():
        messages.error(request, 'No se puede reservar esta función porque ya pasó.')
        return redirect('salas:lista_funciones')
    
    if not funcion.disponible:
        messages.error(request, 'Esta función no está disponible.')
        return redirect('salas:lista_funciones')

    ############################################################################
    # ─── Timer de sesión ────────────────────────────────────────
    # Se guarda el momento exacto en que el usuario entró a esta pantalla. El mismo timer cubre selección de asientos + pago.
    # Guardar el momento en que el usuario entró a seleccionar asientos
    # Esto define el inicio del contador de tiempo
    clave_sesion = f'inicio_seleccion_{funcion_id}'
    if clave_sesion not in request.session:
        request.session[clave_sesion] = timezone.now().isoformat()
 
    inicio_seleccion_iso = request.session[clave_sesion]
    tiempo_limite = get_tiempo_limite()
 
    # Calcular segundos restantes desde que entró a la página
    # from datetime import datetime
    inicio_dt = datetime.fromisoformat(inicio_seleccion_iso)
    # Hacer aware si es naive
    if timezone.is_naive(inicio_dt):
        inicio_dt = timezone.make_aware(inicio_dt)
 
    tiempo_transcurrido = (timezone.now() - inicio_dt).total_seconds()
    segundos_restantes = max(0, int(tiempo_limite * 60 - tiempo_transcurrido))
 
    # Si ya expiró antes de confirmar, reiniciar sesión y avisar
    if segundos_restantes <= 0:
        del request.session[clave_sesion]
        messages.warning(request, '⏰ El tiempo expiró. El contador se reinició.')
        request.session[clave_sesion] = timezone.now().isoformat()
        segundos_restantes = tiempo_limite * 60

    # ─────────────────────────────────────────────────────────────
    ############################################################################

    asientos_ocupados = funcion.asientos_ocupados()
    layout = funcion.sala.layout_asientos()
    max_asientos = get_max_asientos()
    
    contexto = {
        'funcion': funcion,
        'sala': funcion.sala,
        'layout': layout,
        'asientos_ocupados': asientos_ocupados,
        'asientos_disponibles': funcion.asientos_disponibles(),
        'max_asientos': max_asientos,
        'tiempo_limite_minutos': tiempo_limite,
        'segundos_restantes': segundos_restantes,
    }
    
    return render(request, 'reservas/seleccionar_asientos.html', contexto)


@login_required
def confirmar_reserva_con_asientos(request, funcion_id):
    """Procesa la reserva con los asientos seleccionados. Verifica que el timer de sesión no haya expirado antes de crear la reserva."""
    if request.method != 'POST':
        return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)
    
    funcion = get_object_or_404(Funcion, id=funcion_id)
    asientos_seleccionados = request.POST.get('asientos_seleccionados', '')
    max_asientos = get_max_asientos()
    tiempo_limite = get_tiempo_limite()

    # ─── Verificar timer de sesión ───────────────────────────────
    # El timer empezó en seleccionar_asientos. Si llegó aquí con tiempo
    # suficiente, usamos los segundos restantes como fecha_limite_pago.

    if not asientos_seleccionados:
        messages.error(request, 'Debes seleccionar al menos un asiento.')
        return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)
    
    asientos_lista = asientos_seleccionados.split(',')
    cantidad = len(asientos_lista)
    ################################################################################
    """
    # Validar cantidad
    if cantidad < 1 or cantidad > max_asientos:
        messages.error(request, f'Debés seleccionar entre 1 y {max_asientos} asientos.')
        return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)
 
    # Validar disponibilidad
    asientos_ocupados = funcion.asientos_ocupados()
    for asiento in asientos_lista:
        if asiento in asientos_ocupados:
            messages.error(request, f'El asiento {asiento} ya no está disponible.')
            return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)
    """
    # VALIDACIÓN: Verificar que los asientos estén disponibles
    asientos_ocupados = funcion.asientos_ocupados()
    for asiento in asientos_lista:
        if asiento in asientos_ocupados:
            messages.error(request, f'El asiento {asiento} ya no está disponible. Por favor, seleccioná otros asientos.')
            return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)
                        # FIJARSE ACA QUE LA CANTIDAD DEBE IR PRIMERO 
    # Validar cantidad
    if cantidad < 1 or cantidad > max_asientos:
        messages.error(request, f'Debés seleccionar entre 1 y {max_asientos} asientos.')
        return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)
    ################################################################################

    # Calcular fecha_limite_pago desde el inicio de la sesión de selección
    clave_sesion = f'inicio_seleccion_{funcion_id}'
    fecha_limite_pago = None

    if clave_sesion in request.session:
        # from datetime import datetime
        inicio_iso = request.session.pop(clave_sesion)
        inicio_dt = datetime.fromisoformat(inicio_iso)
        
        if timezone.is_naive(inicio_dt):
            inicio_dt = timezone.make_aware(inicio_dt)
        fecha_limite_calculada = inicio_dt + timedelta(minutes=tiempo_limite)
        # Garantizar al menos 1 minuto para confirmar
        fecha_limite_pago = max(fecha_limite_calculada, timezone.now() + timedelta(minutes=1))
        
        if fecha_limite_calculada <= timezone.now():
            messages.error(request, '⏰ El tiempo expiró. Por favor, comenzá de nuevo.')
            return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)

    else:
        fecha_limite_pago = timezone.now() + timedelta(minutes=tiempo_limite)

    
    # Crear la reserva con los asientos seleccionados
    reserva = Reserva.objects.create(
        usuario=request.user,
        funcion=funcion,
        cantidad_entradas=cantidad,
        asientos_seleccionados=asientos_seleccionados,
        fecha_limite_pago=fecha_limite_pago,
    )
    
    msg_base = (
        f'✅ Reserva creada. Asientos: {reserva.asientos_formateados()}. '
        f'Código: {reserva.codigo_reserva}. '
        f'Tenés {tiempo_limite} minutos en total para completar el pago.'
    )
    if EMAIL_DISPONIBLE:
        try:
            enviar_email_confirmacion_reserva(reserva, request)
            messages.success(request, msg_base)
        except Exception:
            messages.success(request, msg_base)
    else:
        messages.success(request, msg_base)
    return redirect('reservas:detalle_reserva', reserva_id=reserva.id)


@login_required
def verificar_asientos_disponibles(request, funcion_id):
    """API endpoint para verificar en tiempo real qué asientos están disponibles."""
    funcion = get_object_or_404(Funcion, id=funcion_id)
    asientos_ocupados = funcion.asientos_ocupados()
    
    return JsonResponse({
        'success': True,
        'asientos_ocupados': asientos_ocupados,
        'total_disponibles': funcion.asientos_disponibles()
    })


@login_required
def crear_reserva(request, funcion_id):
    """Vista antigua - redirige a selección de asientos."""
    return redirect('reservas:seleccionar_asientos', funcion_id=funcion_id)


# ============================================
# VISTAS PRINCIPALES
# ============================================

@login_required
def mis_reservas(request):
    mostrar_canceladas = request.GET.get('mostrar_canceladas', 'si')
    mostrar_expiradas = request.GET.get('mostrar_expiradas', 'si')
    
    reservas = Reserva.objects.filter(usuario=request.user).select_related('funcion__pelicula', 'funcion__sala')
    
    # Auto-cancelar reservas que expiraron por tiempo
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
    
    if reserva.cancelar_por_tiempo_expirado():
        messages.warning(request, f'⏰ Esta reserva fue cancelada automáticamente porque expiró el tiempo de pago ({get_tiempo_limite()} minutos).')
    
    if reserva.actualizar_estado_si_expiro():
        messages.info(request, 'Esta reserva ha expirado porque la función ya pasó.')
    
    # NUEVO: Generar QR si la reserva está confirmada y tiene pago
    qr_imagen = None
    if reserva.estado == 'confirmada' and hasattr(reserva, 'pago') and reserva.pago.codigo_qr:
        if QR_DISPONIBLE:
            try:
                qr_imagen = generar_qr_imagen(reserva.pago.codigo_qr)
            except Exception as e:
                print(f"Error generando QR: {e}")
    
    contexto = {
        'reserva': reserva,
        'qr_imagen': qr_imagen,
    }
    return render(request, 'reservas/detalle_reserva.html', contexto)


@login_required
def cancelar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    
    reserva.cancelar_por_tiempo_expirado()
    reserva.actualizar_estado_si_expiro()
    
    if not reserva.funcion.puede_cancelarse():
        messages.error(request, 'No se puede cancelar esta reserva. Debe hacerlo al menos 2 horas antes de la función.')
        return redirect('reservas:mis_reservas')
    
    if reserva.estado == 'pendiente':
        reserva.estado = 'cancelada'
        reserva.save()
        
        if EMAIL_DISPONIBLE:
            try:
                enviar_email_cancelacion_reserva(reserva)
                messages.success(request, '✅ Reserva cancelada exitosamente. Te enviamos un email de confirmación.')
            except Exception:
                messages.success(request, '✅ Reserva cancelada exitosamente.')
        else:
            messages.success(request, '✅ Reserva cancelada exitosamente.')
    else:
        messages.error(request, 'No se puede cancelar esta reserva.')
    
    return redirect('reservas:mis_reservas')


@login_required
def eliminar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    
    if reserva.estado in ['cancelada', 'expirada']:
        codigo = reserva.codigo_reserva
        reserva.delete()
        messages.success(request, f'Reserva {codigo} eliminada del historial.')
    else:
        messages.error(request, 'Solo se pueden eliminar reservas canceladas o expiradas.')
    
    return redirect('reservas:mis_reservas')