from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from decimal import Decimal
from .models import Cupon, PromocionDia, Combo, CuponUsado


@login_required
def mis_cupones(request):
    """Historial de cupones usados por el usuario."""
    historial = CuponUsado.objects.filter(
        usuario=request.user
    ).select_related('cupon', 'reserva', 'reserva__funcion__pelicula')

    contexto = {'historial': historial}
    return render(request, 'promociones/mis_cupones.html', contexto)


@login_required
def lista_combos(request):
    """Lista de combos disponibles."""
    combos = Combo.objects.filter(activo=True)

    # Promociones activas hoy
    dia_actual = timezone.now().weekday()
    promos_hoy = PromocionDia.objects.filter(dia_semana=dia_actual, activo=True)

    contexto = {
        'combos': combos,
        'promos_hoy': promos_hoy,
    }
    return render(request, 'promociones/lista_combos.html', contexto)


@csrf_exempt
def verificar_cupon_api(request):
    """
    API para verificar un código de cupón y calcular el descuento.
    Recibe: codigo_cupon, monto (float)
    Retorna: JSON con validez, descuento y monto final.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    codigo = request.POST.get('codigo', '').strip().upper()
    try:
        monto = Decimal(str(request.POST.get('monto', '0')))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Monto inválido'})

    if not codigo:
        return JsonResponse({'success': False, 'error': 'Ingresá un código'})

    try:
        cupon = Cupon.objects.get(codigo=codigo)
    except Cupon.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Código no encontrado'})

    # Validar vigencia y usos
    valido, mensaje = cupon.es_valido()
    if not valido:
        return JsonResponse({'success': False, 'error': mensaje})

    # Validar monto mínimo
    if cupon.monto_minimo and monto < cupon.monto_minimo:
        return JsonResponse({
            'success': False,
            'error': f'El monto mínimo para este cupón es ${cupon.monto_minimo}'
        })

    # Validar primera compra
    if cupon.solo_primera_compra and request.user.is_authenticated:
        ya_compro = CuponUsado.objects.filter(usuario=request.user).exists()
        if ya_compro:
            return JsonResponse({
                'success': False,
                'error': 'Este cupón es solo para tu primera compra'
            })

    # Validar que no haya usado ya este cupón
    if request.user.is_authenticated:
        ya_uso = CuponUsado.objects.filter(
            cupon=cupon, usuario=request.user
        ).exists()
        if ya_uso:
            return JsonResponse({
                'success': False,
                'error': 'Ya utilizaste este cupón anteriormente'
            })

    descuento = cupon.calcular_descuento(monto)
    monto_final = max(monto - descuento, Decimal('0'))

    return JsonResponse({
        'success': True,
        'codigo': cupon.codigo,
        'descripcion': cupon.descripcion,
        'tipo': cupon.tipo,
        'valor': float(cupon.valor),
        'descuento': float(descuento),
        'monto_final': float(monto_final),
    })


def promociones_dia_api(request):
    """
    API pública que retorna las promociones activas para el día de hoy.
    Usada en procesar_pago para mostrar descuentos automáticos.
    """
    dia_actual = timezone.now().weekday()
    promos = PromocionDia.objects.filter(dia_semana=dia_actual, activo=True)

    data = []
    for promo in promos:
        data.append({
            'id': promo.id,
            'nombre': promo.nombre,
            'tipo': promo.tipo,
            'descripcion': promo.descripcion,
            'porcentaje': float(promo.porcentaje_descuento) if promo.porcentaje_descuento else None,
        })

    return JsonResponse({'success': True, 'dia': dia_actual, 'promociones': data})