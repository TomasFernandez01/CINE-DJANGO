# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from datetime import timedelta
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from pagos.models import Pago
from promociones.models import Cupon, PromocionDia, Combo, CuponUsado
from ..decorators import staff_required
from ..forms import (
    ComboForm,
    CuponForm,
    PromocionDiaForm,
)


# ============================================================
# PROMOCIONES — COMBOS
# ============================================================

@staff_required
def combos_lista(request):
    combos = Combo.objects.all().order_by('precio')
    return render(request, 'panel/promociones/combos/lista.html', {
        'combos': combos,
        'seccion_activa': 'combos',
    })


@staff_required
def combos_crear(request):
    if request.method == 'POST':
        form = ComboForm(request.POST, request.FILES)
        if form.is_valid():
            combo = form.save()
            messages.success(request, f'✅ Combo "{combo.nombre}" creado.')
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:combos_crear')
            return redirect('panel:combos_lista')
    else:
        form = ComboForm()

    return render(request, 'panel/promociones/combos/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Combo',
        'accion': 'crear',
        'seccion_activa': 'combos',
    })


@staff_required
def combos_editar(request, combo_id):
    combo = get_object_or_404(Combo, id=combo_id)

    if request.method == 'POST':
        form = ComboForm(request.POST, request.FILES, instance=combo)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Combo "{combo.nombre}" actualizado.')
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:combos_crear')
            return redirect('panel:combos_lista')
    else:
        form = ComboForm(instance=combo)

    return render(request, 'panel/promociones/combos/form.html', {
        'form': form,
        'objeto': combo,
        'titulo_pagina': f'Editar: {combo.nombre}',
        'accion': 'editar',
        'seccion_activa': 'combos',
    })

@staff_required
@require_POST
def combos_eliminar(request):
    """
    Borrado múltiple de combos, en dos pasos (mismo patrón que salas_eliminar).
    A diferencia de Sala/Pelicula/Funcion, Combo NO borra en cascada: los Pagos
    que lo usaron quedan con combo=null (Pago.combo es on_delete=SET_NULL).
    """
    ids = request.POST.getlist('seleccionadas')
    if not ids:
        messages.error(request, 'No seleccionaste ningún combo.')
        return redirect('panel:combos_lista')

    combos_qs = Combo.objects.filter(id__in=ids)
    if not combos_qs.exists():
        messages.error(request, 'Los combos seleccionados ya no existen.')
        return redirect('panel:combos_lista')

    if request.POST.get('confirmado') == '1':
        nombres = list(combos_qs.values_list('nombre', flat=True))
        combos_qs.delete()
        messages.success(request, f'🗑️ Combo(s) eliminado(s): {", ".join(nombres)}.')
        return redirect('panel:combos_lista')

    # Paso 1: vista previa (no hay cascada, solo informamos pagos que quedarían sin combo)
    resumen = []
    for combo in combos_qs:
        total_pagos = Pago.objects.filter(combo=combo).count()
        resumen.append({
            'combo': combo,
            'total_pagos': total_pagos,
        })

    return render(request, 'panel/promociones/combos/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
        'seccion_activa': 'combos',
    })

# ============================================================
# PROMOCIONES — CUPONES
# ============================================================

@staff_required
def cupones_lista(request):
    busqueda = request.GET.get('q', '')
    estado = request.GET.get('estado', '')

    cupones = Cupon.objects.all().order_by('-fecha_inicio')
    if busqueda:
        cupones = cupones.filter(
            Q(codigo__icontains=busqueda) | Q(descripcion__icontains=busqueda)
        )
    if estado == 'activo':
        cupones = cupones.filter(activo=True)
    elif estado == 'inactivo':
        cupones = cupones.filter(activo=False)

    contexto = {
        'cupones': cupones,
        'busqueda': busqueda,
        'estado': estado,
        'total': cupones.count(),
        'seccion_activa': 'cupones',
    }
    return render(request, 'panel/promociones/cupones/lista.html', contexto)


@staff_required
def cupones_crear(request):
    if request.method == 'POST':
        form = CuponForm(request.POST)
        if form.is_valid():
            cupon = form.save()
            messages.success(request, f'✅ Cupón "{cupon.codigo}" creado.')
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:cupones_crear')
            return redirect('panel:cupones_lista')
    else:
        form = CuponForm()

    return render(request, 'panel/promociones/cupones/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Cupón',
        'accion': 'crear',
        'seccion_activa': 'cupones',
    })


@staff_required
def cupones_editar(request, cupon_id):
    cupon = get_object_or_404(Cupon, id=cupon_id)

    if request.method == 'POST':
        form = CuponForm(request.POST, instance=cupon)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Cupón "{cupon.codigo}" actualizado.')
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:cupones_crear')
            return redirect('panel:cupones_lista')
    else:
        form = CuponForm(instance=cupon)

    return render(request, 'panel/promociones/cupones/form.html', {
        'form': form,
        'objeto': cupon,
        'titulo_pagina': f'Editar: {cupon.codigo}',
        'accion': 'editar',
        'seccion_activa': 'cupones',
    })

@staff_required
@require_POST
def cupones_eliminar(request):
    """
    Borrado múltiple de cupones, en dos pasos (mismo patrón que salas_eliminar).
    Cupon SÍ borra en cascada su historial de usos (CuponUsado.cupon es CASCADE),
    pero los Pagos que lo usaron quedan con cupon_usado=null (SET_NULL), no se borran.
    """
    ids = request.POST.getlist('seleccionadas')
    if not ids:
        messages.error(request, 'No seleccionaste ningún cupón.')
        return redirect('panel:cupones_lista')

    cupones_qs = Cupon.objects.filter(id__in=ids)
    if not cupones_qs.exists():
        messages.error(request, 'Los cupones seleccionados ya no existen.')
        return redirect('panel:cupones_lista')

    if request.POST.get('confirmado') == '1':
        codigos = list(cupones_qs.values_list('codigo', flat=True))
        cupones_qs.delete()  # cascada: borra también su historial de usos (CuponUsado)
        messages.success(request, f'🗑️ Cupón(es) eliminado(s): {", ".join(codigos)}.')
        return redirect('panel:cupones_lista')

    # Paso 1: vista previa de lo que se va a borrar en cascada
    resumen = []
    for cupon in cupones_qs:
        total_usos = cupon.usos.count()
        resumen.append({
            'cupon': cupon,
            'total_usos': total_usos,
        })

    return render(request, 'panel/promociones/cupones/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
        'seccion_activa': 'cupones',
    })

# ============================================================
# PROMOCIONES — PROMOCIÓN POR DÍA
# ============================================================

@staff_required
def promodia_lista(request):
    promociones = PromocionDia.objects.all().order_by('dia_semana')
    return render(request, 'panel/promociones/promodia/lista.html', {
        'promociones': promociones,
        'seccion_activa': 'promodia',
    })


@staff_required
def promodia_crear(request):
    if request.method == 'POST':
        form = PromocionDiaForm(request.POST)
        if form.is_valid():
            promo = form.save()
            messages.success(request, f'✅ Promoción "{promo.nombre}" creada.')
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:promodia_crear')
            return redirect('panel:promodia_lista')
    else:
        form = PromocionDiaForm()

    return render(request, 'panel/promociones/promodia/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Promoción por Día',
        'accion': 'crear',
        'seccion_activa': 'promodia',
    })


@staff_required
def promodia_editar(request, promo_id):
    promo = get_object_or_404(PromocionDia, id=promo_id)

    if request.method == 'POST':
        form = PromocionDiaForm(request.POST, instance=promo)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Promoción "{promo.nombre}" actualizada.')
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:promodia_crear')
            return redirect('panel:promodia_lista')
    else:
        form = PromocionDiaForm(instance=promo)

    return render(request, 'panel/promociones/promodia/form.html', {
        'form': form,
        'objeto': promo,
        'titulo_pagina': f'Editar: {promo.nombre}',
        'accion': 'editar',
        'seccion_activa': 'promodia',
    })

@staff_required
@require_POST
def promodia_eliminar(request):
    """
    Borrado múltiple de promociones por día, en dos pasos (mismo patrón que
    salas_eliminar). PromocionDia NO borra en cascada: los Pagos que la usaron
    quedan con promo_dia=null (Pago.promo_dia es on_delete=SET_NULL).
    """
    ids = request.POST.getlist('seleccionadas')
    if not ids:
        messages.error(request, 'No seleccionaste ninguna promoción.')
        return redirect('panel:promodia_lista')

    promos_qs = PromocionDia.objects.filter(id__in=ids)
    if not promos_qs.exists():
        messages.error(request, 'Las promociones seleccionadas ya no existen.')
        return redirect('panel:promodia_lista')

    if request.POST.get('confirmado') == '1':
        nombres = list(promos_qs.values_list('nombre', flat=True))
        promos_qs.delete()
        messages.success(request, f'🗑️ Promoción(es) eliminada(s): {", ".join(nombres)}.')
        return redirect('panel:promodia_lista')

    # Paso 1: vista previa (no hay cascada, solo informamos pagos que quedarían sin promo)
    resumen = []
    for promo in promos_qs:
        total_pagos = Pago.objects.filter(promo_dia=promo).count()
        resumen.append({
            'promo': promo,
            'total_pagos': total_pagos,
        })

    return render(request, 'panel/promociones/promodia/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
        'seccion_activa': 'promodia',
    })



# ============================================================
# CUPONES USADOS (solo lectura) — vive en Operaciones
# ============================================================

@staff_required
def cupones_usados_lista(request):
    busqueda = request.GET.get('q', '')

    historial = CuponUsado.objects.select_related(
        'cupon', 'usuario', 'reserva__funcion__pelicula'
    ).order_by('-fecha_uso')

    if busqueda:
        historial = historial.filter(
            Q(cupon__codigo__icontains=busqueda) |
            Q(usuario__username__icontains=busqueda)
        )

    contexto = {
        'historial': historial[:100],
        'busqueda': busqueda,
        'total': historial.count(),
        'seccion_activa': 'cupones_usados',
    }
    return render(request, 'panel/promociones/cupones_usados/lista.html', contexto)

# ============================================================
#   STAFFV2 stadisticas de cupones
# ============================================================

@staff_required
def cupones_estadisticas(request):
    """Estadísticas de uso de cupones (único dato realmente trackeado hoy)."""
    ahora = timezone.now()
    hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    semana = hoy - timedelta(days=7)
    mes = hoy - timedelta(days=30)

    usos_hoy = CuponUsado.objects.filter(fecha_uso__gte=hoy)
    usos_semana = CuponUsado.objects.filter(fecha_uso__gte=semana)
    usos_mes = CuponUsado.objects.filter(fecha_uso__gte=mes)

    stats = {
        'usos_hoy': usos_hoy.count(),
        'usos_semana': usos_semana.count(),
        'usos_mes': usos_mes.count(),
        'usos_total': CuponUsado.objects.count(),
        'descuento_hoy': usos_hoy.aggregate(t=Sum('descuento_aplicado'))['t'] or 0,
        'descuento_semana': usos_semana.aggregate(t=Sum('descuento_aplicado'))['t'] or 0,
        'descuento_mes': usos_mes.aggregate(t=Sum('descuento_aplicado'))['t'] or 0,
        'descuento_total': CuponUsado.objects.aggregate(t=Sum('descuento_aplicado'))['t'] or 0,
    }

    # Ranking histórico de cupones más usados
    top_cupones = CuponUsado.objects.values(
        'cupon__codigo', 'cupon__descripcion'
    ).annotate(
        veces_usado=Count('id'),
        descuento_generado=Sum('descuento_aplicado')
    ).order_by('-veces_usado')[:10]

    # Cupones activos que no se usaron en los últimos 30 días (candidatos a revisar)
    cupones_activos_sin_uso = Cupon.objects.filter(
        activo=True
    ).exclude(
        id__in=usos_mes.values_list('cupon_id', flat=True)
    ).order_by('-fecha_inicio')[:10]

    ultimos_usos = CuponUsado.objects.select_related(
        'cupon', 'usuario', 'reserva__funcion__pelicula'
    ).order_by('-fecha_uso')[:10]

    contexto = {
        'stats': stats,
        'top_cupones': top_cupones,
        'cupones_activos_sin_uso': cupones_activos_sin_uso,
        'ultimos_usos': ultimos_usos,
        'seccion_activa': 'cupones',
    }
    return render(request, 'panel/promociones/cupones/estadisticas.html', contexto)

