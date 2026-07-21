from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from decimal import Decimal
from .models import Pago
from reservas.models import Reserva
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
try:
    from promociones.models import Cupon, PromocionDia, Combo, CuponUsado
    PROMOCIONES_DISPONIBLE = True
except ImportError:
    PROMOCIONES_DISPONIBLE = False

# ============================================================
# HELPERS DE PROMOCIONES
# ============================================================
 
def _obtener_promo_dia():
    """Retorna la PromocionDia activa para hoy, o None."""
    if not PROMOCIONES_DISPONIBLE:
        return None
    dia_actual = timezone.now().weekday()
    return PromocionDia.objects.filter(dia_semana=dia_actual, activo=True).first()
 
def _obtener_combos():
    """Retorna combos activos."""
    if not PROMOCIONES_DISPONIBLE:
        return []
    return Combo.objects.filter(activo=True)
 
def _calcular_descuentos(monto_original, cantidad_entradas, codigo_cupon, combo_id, usuario, promo_dia):
    """
    Calcula todos los descuentos y retorna un dict con los resultados.
    La promo_dia y el cupón se aplican sobre el monto de entradas.
    El combo es un adicional.
    """
    descuento_promo = Decimal('0')
    descuento_cupon_val = Decimal('0')
    cupon_obj = None
    combo_obj = None
    promo_dia_obj = None
    error_cupon = None
 
    # 1. Promo del día
    if promo_dia:
        descuento_promo = promo_dia.calcular_descuento(monto_original, cantidad_entradas)
        promo_dia_obj = promo_dia
 
    # 2. Cupón
    if codigo_cupon and PROMOCIONES_DISPONIBLE:
        codigo_cupon = codigo_cupon.upper().strip()
        try:
            cupon = Cupon.objects.get(codigo=codigo_cupon)
            valido, msg = cupon.es_valido()
 
            if not valido:
                error_cupon = msg
            elif cupon.monto_minimo and monto_original < cupon.monto_minimo:
                error_cupon = f'Monto mínimo para este cupón: ${cupon.monto_minimo}'
            elif cupon.solo_primera_compra and CuponUsado.objects.filter(usuario=usuario).exists():
                error_cupon = 'Cupón solo válido para primera compra'
            elif CuponUsado.objects.filter(cupon=cupon, usuario=usuario).exists():
                error_cupon = 'Ya utilizaste este cupón'
            else:
                descuento_cupon_val = cupon.calcular_descuento(monto_original)
                cupon_obj = cupon
        except Cupon.DoesNotExist:
            error_cupon = 'Código de cupón no encontrado'
 
    # 3. Combo
    if combo_id and PROMOCIONES_DISPONIBLE:
        try:
            combo_obj = Combo.objects.get(id=combo_id, activo=True)
        except Combo.DoesNotExist:
            combo_obj = None
 
    descuento_total = descuento_promo + descuento_cupon_val
    precio_combo = combo_obj.precio if combo_obj else Decimal('0')
    monto_final = max(monto_original - descuento_total, Decimal('0')) + precio_combo
 
    return {
        'monto_original': monto_original,
        'descuento_promo_dia': descuento_promo,
        'descuento_cupon': descuento_cupon_val,
        'descuento_total': descuento_total,
        'precio_combo': precio_combo,
        'monto_final': monto_final,
        'cupon_obj': cupon_obj,
        'combo_obj': combo_obj,
        'promo_dia_obj': promo_dia_obj,
        'error_cupon': error_cupon,
    }

# ============================================================
# modificado: NUEVO — PASO 4 DEL FLUJO REORDENADO
# Asientos -> [ESTE PASO: combo] -> Pago
# Antes el combo se elegía adentro de procesar_pago, mezclado con el
# método de pago. Ahora es su paso propio, como en Cinemark.
# ============================================================
@login_required
def elegir_combo(request, reserva_id):
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

    combos = _obtener_combos()

    if request.method == 'POST':
        combo_id = request.POST.get('combo_id', '').strip()
        try:
            cantidad_combo = int(request.POST.get('cantidad_combo', 1))
        except (TypeError, ValueError):
            cantidad_combo = 1
        cantidad_combo = max(1, min(cantidad_combo, 10)) 
        # modificado (Fase E): ahora se guarda un dict {combo_id, cantidad} en vez de solo el id — procesar_pago ya sabe leer ambos formatos (por compatibilidad, si combo_id viene vacío se guarda None)
        request.session[f'combo_reserva_{reserva.id}'] = (
            {'combo_id': combo_id, 'cantidad': cantidad_combo} if combo_id else None
        )
        return redirect('pagos:procesar_pago', reserva_id=reserva.id)

    contexto = {
        'reserva': reserva,
        'combos': combos,
        'total_entradas': reserva.total(),
    }
    return render(request, 'pagos/elegir_combo.html', contexto)

# ============================================================
# VISTAS PRINCIPALES
# ============================================================
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
    
    #---------------------------------------------------------------------
    #promo_dia = _obtener_promo_dia(); combos = _obtener_combos(); monto_original = reserva.total()
    
    # modificado: promo_dia/cupón ya se eligieron y validaron en el paso 2 ("elegir-entrada"), y el combo en el paso 4 ("elegir-combo"). Esta vista ya NO vuelve a pedirlos por formulario — los lee de la sesión, guardada scoped por reserva.id en esos dos pasos. Antes acá se llamaba a _obtener_promo_dia(), que buscaba la promo del DÍA DE HOY (timezone.now().weekday()) en vez del día de la FUNCIÓN — quedaba mal si pagabas un día distinto al de la función. Ahora se usa el promo_dia_id que ya se resolvió correctamente en el paso 2 con el día de la función.
    datos_promo = request.session.get(f'promo_reserva_{reserva.id}', {}) or {}
    codigo_cupon = datos_promo.get('cupon_codigo') or ''
    promo_dia = None
    if datos_promo.get('promo_dia_id') and PROMOCIONES_DISPONIBLE:
        promo_dia = PromocionDia.objects.filter(id=datos_promo['promo_dia_id'], activo=True).first()

    # modificado (Fase E): combo_reserva_<id> ahora guarda un dict
    # {combo_id, cantidad} en vez de solo el id — se soporta también el
    # formato viejo (un string con solo el id) por si quedó algo en sesión
    # de antes de este cambio.
    datos_combo = request.session.get(f'combo_reserva_{reserva.id}')
    combo_id = None
    cantidad_combo = 1
    if isinstance(datos_combo, dict):
        combo_id = datos_combo.get('combo_id')
        cantidad_combo = datos_combo.get('cantidad', 1) or 1
    elif datos_combo:
        combo_id = datos_combo
    #combo_id = request.session.get(f'combo_reserva_{reserva.id}')
    
    monto_original = reserva.total()

    calc = _calcular_descuentos(
        monto_original=monto_original,
        cantidad_entradas=reserva.cantidad_entradas,
        codigo_cupon=codigo_cupon,
        combo_id=combo_id,
        usuario=request.user,
        promo_dia=promo_dia,
    )
    if calc['error_cupon']:
        # El cupón se validó en el paso 2, pero puede haber cambiado algo entre medio (se agotó, venció) — avisamos y seguimos sin él.
        messages.warning(request, f'⚠️ Cupón inválido: {calc["error_cupon"]}. El pago se procesará sin descuento por cupón.')
        calc['descuento_cupon'] = Decimal('0')
        calc['cupon_obj'] = None
        calc['descuento_total'] = calc['descuento_promo_dia']
        calc['monto_final'] = max(monto_original - calc['descuento_total'], Decimal('0')) + calc['precio_combo']
    # modificado (Fase E): _calcular_descuentos no sabe de cantidad, calcula
    # el precio de 1 solo combo — acá se multiplica por la cantidad elegida
    if calc['combo_obj']:
        calc['precio_combo'] = calc['precio_combo'] * cantidad_combo
        calc['monto_final'] = max(monto_original - calc['descuento_total'], Decimal('0')) + calc['precio_combo']
    else:
        cantidad_combo = 1
        
    #---------------------------------------------------------------------
    if request.method == 'POST':
        if reserva.expiro_tiempo_pago():
            reserva.estado = 'cancelada'
            reserva.save()
            messages.error(request, '⏰ Lo sentimos, el tiempo de pago expiró mientras procesabas la transacción. Por favor, creá una nueva reserva.')
            return redirect('salas:lista_funciones')
    #---------------------------------------------------------------------
        # AHORA SI SE CREA EL PAGO
        metodo_pago = request.POST.get('metodo_pago')
        # MODIFICACION
        # codigo_cupon = request.POST.get('codigo_cupon', '').strip()
        # combo_id = request.POST.get('combo_id', '').strip()
        # calc = _calcular_descuentos(
        #     monto_original=monto_original,
        #     cantidad_entradas=reserva.cantidad_entradas,
        #     codigo_cupon=codigo_cupon,
        #     combo_id=combo_id if combo_id else None,
        #     usuario=request.user,
        #     promo_dia=promo_dia,
        # )
        # if calc['error_cupon']:
        #     messages.warning(request, f'⚠️ Cupón inválido: {calc["error_cupon"]}. El pago se procesará sin descuento por cupón.')
        #     calc['descuento_cupon'] = Decimal('0')
        #     calc['cupon_obj'] = None
        #     calc['descuento_total'] = calc['descuento_promo_dia']
        #     calc['monto_final'] = max(monto_original - calc['descuento_total'], Decimal('0')) + calc['precio_combo']
        # # Antes
        # pago = Pago.objects.create( reserva=reserva, metodo_pago=metodo_pago, monto=reserva.total(), estado='aprobado')
        # Crear el pago
        pago = Pago.objects.create(
            reserva=reserva,
            metodo_pago=metodo_pago,
            monto_original=monto_original,
            descuento_cupon=calc['descuento_cupon'],
            descuento_promo_dia=calc['descuento_promo_dia'],
            descuento_total=calc['descuento_total'],
            precio_combo=calc['precio_combo'],
            cantidad_combo=cantidad_combo,
            monto=calc['monto_final'],
            estado='aprobado',
            cupon_usado=calc['cupon_obj'],
            combo=calc['combo_obj'],
            promo_dia=calc['promo_dia_obj'],
        )
        # DATOS DE TARJETA
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
        #-----------------------------------------------------------
        # Registrar uso del cupón
        if calc['cupon_obj'] and PROMOCIONES_DISPONIBLE:
            CuponUsado.objects.create(
                cupon=calc['cupon_obj'],
                usuario=request.user,
                reserva=reserva,
                descuento_aplicado=calc['descuento_cupon'],
            )
            calc['cupon_obj'].usos_actuales += 1
            calc['cupon_obj'].save(update_fields=['usos_actuales'])
        #-----------------------------------------------------------
        # modificado: ya no hace falta esta info en sesión, se limpia
        request.session.pop(f'promo_reserva_{reserva.id}', None)
        request.session.pop(f'combo_reserva_{reserva.id}', None)

        if EMAIL_DISPONIBLE:
            try:
                enviar_email_pago_confirmado(pago, request)
                messages.success(request, f'¡Pago procesado exitosamente! Número de transacción: {pago.numero_transaccion}. Te enviamos un email con el comprobante y código QR.')
            except Exception as e:
                messages.success(request, f'¡Pago procesado exitosamente! Número de transacción: {pago.numero_transaccion}')
                messages.warning(request, 'No pudimos enviar el email, pero tu pago está confirmado.')
        else:
            messages.success(request, f'¡Pago procesado exitosamente! Número de transacción: {pago.numero_transaccion}')
        
        return redirect('pagos:comprobante_pago', pago_id=pago.id)
    #-----------------------------------------------------------
    # GET — contexto para el template
    # modificado: ya no manda 'combos' (se eligen en el paso anterior); manda el detalle de lo ya elegido para mostrarlo de solo lectura.
    contexto = {
        'reserva': reserva,
        'total': monto_original,
        'promo_dia': calc['promo_dia_obj'],
        'cupon_obj': calc['cupon_obj'],
        'combo_obj': calc['combo_obj'],
        'descuento_cupon': calc['descuento_cupon'],
        'descuento_promo_dia': calc['descuento_promo_dia'],
        'descuento_total': calc['descuento_total'],
        'precio_combo': calc['precio_combo'],
        'cantidad_combo': cantidad_combo,
        'monto_final': calc['monto_final'],
        # modificado: se calcula acá (no en el template) para evitar la
        # ambigüedad de precedencia de "and/or" en {% if %} de Django
        'mostrar_bloque_promos': PROMOCIONES_DISPONIBLE and (calc['descuento_total'] > 0 or calc['precio_combo'] > 0),
        'promociones_disponible': PROMOCIONES_DISPONIBLE,
    }
    return render(request, 'pagos/procesar_pago.html', contexto)
    #-----------------------------------------------------------

@login_required
def comprobante_pago(request, pago_id):
    pago = get_object_or_404(Pago, id=pago_id, reserva__usuario=request.user)
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
    """Vista para que el personal del cine escanee y verifique QR codes."""
    if not request.user.is_staff:
        messages.error(request, 'No tenés permisos para acceder a esta sección.')
        return redirect('peliculas:inicio')
    
    contexto = {}
    return render(request, 'pagos/verificador_qr.html', contexto)


@csrf_exempt  # Permitir POST desde scanner
def verificar_qr_api(request):
    """API para verificar un código QR.Retorna JSON con el estado del código."""
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
    """API para marcar un QR como escaneado (usado)."""
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