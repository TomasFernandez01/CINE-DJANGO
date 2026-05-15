from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Pago
from reservas.models import Reserva


from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from salas.models import Funcion


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
        messages.error(request, '⏰ Esta reserva fue cancelada automáticamente porque expiró el tiempo de pago. Los asientos han sido liberados.')
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
    
# ============================================================
# PANEL DE ESTADÍSTICAS PARA STAFF
# ============================================================
 
@login_required
def estadisticas_staff(request):
    """
    Panel de estadísticas para staff.
    Muestra métricas de ventas, ocupación y escaneos.
    """
    if not request.user.is_staff:
        messages.error(request, 'No tenés permisos para acceder a esta sección.')
        return redirect('peliculas:inicio')
 
    ahora = timezone.now()
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    semana_inicio = hoy_inicio - timedelta(days=7)
 
    # ---- RESUMEN GENERAL ----
    total_pagos_aprobados = Pago.objects.filter(estado='aprobado').count()
    total_recaudado = Pago.objects.filter(
        estado='aprobado'
    ).aggregate(total=Sum('monto'))['total'] or 0
 
    pagos_hoy = Pago.objects.filter(
        estado='aprobado',
        fecha_pago__gte=hoy_inicio
    )
    recaudado_hoy = pagos_hoy.aggregate(total=Sum('monto'))['total'] or 0
    entradas_hoy = pagos_hoy.aggregate(
        total=Sum('reserva__cantidad_entradas')
    )['total'] or 0
 
    # ---- QR ----
    qr_escaneados_hoy = Pago.objects.filter(
        qr_escaneado=True,
        fecha_escaneo__gte=hoy_inicio
    ).count()
    qr_total_escaneados = Pago.objects.filter(qr_escaneado=True).count()
    qr_pendientes = Pago.objects.filter(
        estado='aprobado',
        qr_escaneado=False,
        reserva__estado='confirmada',
        reserva__funcion__fecha_hora__gte=ahora
    ).count()
 
    # ---- FUNCIONES DE HOY ----
    funciones_hoy = Funcion.objects.filter(
        fecha_hora__gte=hoy_inicio,
        fecha_hora__lt=hoy_inicio + timedelta(days=1)
    ).select_related('pelicula', 'sala').order_by('fecha_hora')
 
    funciones_con_stats = []
    for f in funciones_hoy:
        reservas_confirmadas = f.reservas.filter(estado='confirmada').count()
        entradas_vendidas = f.reservas.filter(
            estado='confirmada'
        ).aggregate(total=Sum('cantidad_entradas'))['total'] or 0
        capacidad = f.sala.capacidad
        ocupacion_pct = int((entradas_vendidas / capacidad * 100)) if capacidad > 0 else 0
        qr_escaneados = Pago.objects.filter(
            reserva__funcion=f,
            qr_escaneado=True
        ).count()
        funciones_con_stats.append({
            'funcion': f,
            'entradas_vendidas': entradas_vendidas,
            'capacidad': capacidad,
            'ocupacion_pct': ocupacion_pct,
            'qr_escaneados': qr_escaneados,
            'reservas': reservas_confirmadas,
        })
 
    # ---- ÚLTIMOS PAGOS ----
    ultimos_pagos = Pago.objects.filter(
        estado='aprobado'
    ).select_related(
        'reserva__usuario',
        'reserva__funcion__pelicula'
    ).order_by('-fecha_pago')[:10]
 
    # ---- ÚLTIMOS ESCANEOS ----
    ultimos_escaneos = Pago.objects.filter(
        qr_escaneado=True
    ).select_related(
        'reserva__usuario',
        'reserva__funcion__pelicula',
        'reserva__funcion__sala'
    ).order_by('-fecha_escaneo')[:10]
 
    contexto = {
        'ahora': ahora,
        # Resumen
        'total_pagos_aprobados': total_pagos_aprobados,
        'total_recaudado': total_recaudado,
        'recaudado_hoy': recaudado_hoy,
        'entradas_hoy': entradas_hoy,
        # QR
        'qr_escaneados_hoy': qr_escaneados_hoy,
        'qr_total_escaneados': qr_total_escaneados,
        'qr_pendientes': qr_pendientes,
        # Funciones
        'funciones_con_stats': funciones_con_stats,
        # Listas
        'ultimos_pagos': ultimos_pagos,
        'ultimos_escaneos': ultimos_escaneos,
    }
    return render(request, 'pagos/estadisticas_staff.html', contexto)


