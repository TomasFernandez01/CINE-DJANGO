# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from datetime import timedelta
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import JsonResponse  # modificado: respuesta AJAX para eliminar_modal.js
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from pagos.models import Pago
from promociones.models import Cupon, PromocionDia, Combo, CuponUsado
from ..decorators import staff_required, superuser_required  # modificado (T1)
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
    combos = Combo.objects.annotate(
        # modificado: el related_name real en ItemPago es 'items_pago' (no 'pago_items'),
        # causaba FieldError "Cannot resolve keyword 'pago_items' into field"
        unidades_vendidas=Sum('items_pago__cantidad'),  # modificado
        recaudacion_combo=Sum('items_pago__precio_unitario')  # modificado
    ).order_by('-unidades_vendidas', 'precio')

    return render(request, 'panel/promociones/combos/lista.html', {
        'combos': combos,
        'es_super': request.user.is_superuser,
        'seccion_activa': 'combos',
    })


# modificado (T1): crear combos pasa a ser exclusivo de SuperUser (institucional,
# mismo criterio que Cupones y que peliculas_crear).
@superuser_required
def combos_crear(request):
    if request.method == 'POST':
        form = ComboForm(request.POST, request.FILES)
        if form.is_valid():
            combo = form.save()
            messages.success(request, f'Combo "{combo.nombre}" creado.')
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
    es_super = request.user.is_superuser  # modificado (T1)

    if request.method == 'POST':
        form = ComboForm(request.POST, request.FILES, instance=combo)
        if form.is_valid():
            # modificado (T1): Staff (no SuperUser) solo puede activar/
            # desactivar el combo. El modelo Combo no tiene un campo de
            # disponibilidad POR SEDE (no existe ese campo hoy en
            # promociones/models.py); se usa 'activo' como el equivalente
            # más cercano a "disponibilidad local" que pide la consigna.
            # No puede tocar nombre, descripción, precio, categoría ni
            # imagen -- eso queda reservado a SuperUser.
            if not es_super:
                obj = form.save(commit=False)
                original = Combo.objects.get(id=combo.id)
                obj.nombre = original.nombre
                obj.descripcion = original.descripcion
                obj.precio = original.precio
                obj.categoria = original.categoria
                obj.imagen = original.imagen
                obj.save()
                messages.success(request, f'Combo "{combo.nombre}" actualizado (disponibilidad por Staff).')
                return redirect('panel:combos_lista')

            form.save()
            messages.success(request, f'Combo "{combo.nombre}" actualizado.')
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
        'es_super': es_super,  # modificado (T1)
    })

# modificado (T1): eliminar combos pasa a ser exclusivo de SuperUser.
@superuser_required
@require_POST
def combos_eliminar(request):
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    ids = request.POST.getlist('seleccionadas')
    if not ids:
        if es_ajax:
            return JsonResponse({'error': 'No seleccionaste ningún combo.'}, status=400)
        messages.error(request, 'No seleccionaste ningún combo.')
        return redirect('panel:combos_lista')

    combos_qs = Combo.objects.filter(id__in=ids)
    if not combos_qs.exists():
        if es_ajax:
            return JsonResponse({'error': 'Los combos seleccionados ya no existen.'}, status=400)
        messages.error(request, 'Los combos seleccionados ya no existen.')
        return redirect('panel:combos_lista')

    if request.POST.get('confirmado') == '1':
        nombres = list(combos_qs.values_list('nombre', flat=True))
        combos_qs.delete()
        messages.success(request, f'Combo(s) eliminado(s): {", ".join(nombres)}.')
        if es_ajax:
            return JsonResponse({'success': True})
        return redirect('panel:combos_lista')

    resumen = []
    for combo in combos_qs:
        total_pagos = Pago.objects.filter(combo=combo).count()
        resumen.append({
            'combo': combo,
            'total_pagos': total_pagos,
        })

    if es_ajax:
        lineas = [
            f'{item["combo"].nombre}: {item["total_pagos"]} pago(s) quedarían sin combo asociado'
            for item in resumen
        ]
        return JsonResponse({
            'lineas': lineas,
            'advertencia': ('Los combos no se borran en cascada: los pagos que los '
                             'usaron quedan sin combo asociado, no se eliminan.'),
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

    cupones = Cupon.objects.annotate(
        total_usos_realizados=Count('usos'),
        monto_total_descontado=Sum('usos__descuento_aplicado')
    ).order_by('-fecha_inicio')

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
        'es_super': request.user.is_superuser,
        'seccion_activa': 'cupones',
    }
    return render(request, 'panel/promociones/cupones/lista.html', contexto)


# modificado (T1): Cupones son institucionales -- crear queda exclusivo de
# SuperUser. Staff solo tiene acceso de lectura (ver cupones_lista).
@superuser_required
def cupones_crear(request):
    if request.method == 'POST':
        form = CuponForm(request.POST)
        if form.is_valid():
            cupon = form.save()
            messages.success(request, f'Cupón "{cupon.codigo}" creado.')
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


# modificado (T1): editar cupones queda exclusivo de SuperUser (Staff:
# solo lectura, sin excepción de campos -- a diferencia de Salas/Combos acá
# no hay ningún campo "de disponibilidad" que tenga sentido dejarle a Staff).
@superuser_required
def cupones_editar(request, cupon_id):
    cupon = get_object_or_404(Cupon, id=cupon_id)

    if request.method == 'POST':
        form = CuponForm(request.POST, instance=cupon)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cupón "{cupon.codigo}" actualizado.')
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

# modificado (T1): eliminar cupones queda exclusivo de SuperUser.
@superuser_required
@require_POST
def cupones_eliminar(request):
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    ids = request.POST.getlist('seleccionadas')
    if not ids:
        if es_ajax:
            return JsonResponse({'error': 'No seleccionaste ningún cupón.'}, status=400)
        messages.error(request, 'No seleccionaste ningún cupón.')
        return redirect('panel:cupones_lista')

    cupones_qs = Cupon.objects.filter(id__in=ids)
    if not cupones_qs.exists():
        if es_ajax:
            return JsonResponse({'error': 'Los cupones seleccionados ya no existen.'}, status=400)
        messages.error(request, 'Los cupones seleccionados ya no existen.')
        return redirect('panel:cupones_lista')

    if request.POST.get('confirmado') == '1':
        codigos = list(cupones_qs.values_list('codigo', flat=True))
        cupones_qs.delete()
        messages.success(request, f'Cupón(es) eliminado(s): {", ".join(codigos)}.')
        if es_ajax:
            return JsonResponse({'success': True})
        return redirect('panel:cupones_lista')

    resumen = []
    for cupon in cupones_qs:
        total_usos = cupon.usos.count()
        resumen.append({
            'cupon': cupon,
            'total_usos': total_usos,
        })

    if es_ajax:
        lineas = [
            f'{item["cupon"].codigo}: {item["total_usos"]} uso(s) registrado(s)'
            for item in resumen
        ]
        return JsonResponse({
            'lineas': lineas,
            'advertencia': ('Esta acción no se puede deshacer. Se borra también el '
                             'historial de usos del cupón, pero los pagos que lo '
                             'usaron NO se borran (quedan sin cupón asociado).'),
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
            messages.success(request, f'Promoción "{promo.nombre}" creada.')
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
            messages.success(request, f'Promoción "{promo.nombre}" actualizada.')
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
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    ids = request.POST.getlist('seleccionadas')
    if not ids:
        if es_ajax:
            return JsonResponse({'error': 'No seleccionaste ninguna promoción.'}, status=400)
        messages.error(request, 'No seleccionaste ninguna promoción.')
        return redirect('panel:promodia_lista')

    promos_qs = PromocionDia.objects.filter(id__in=ids)
    if not promos_qs.exists():
        if es_ajax:
            return JsonResponse({'error': 'Las promociones seleccionadas ya no existen.'}, status=400)
        messages.error(request, 'Las promociones seleccionadas ya no existen.')
        return redirect('panel:promodia_lista')

    if request.POST.get('confirmado') == '1':
        nombres = list(promos_qs.values_list('nombre', flat=True))
        promos_qs.delete()
        messages.success(request, f'Promoción(es) eliminada(s): {", ".join(nombres)}.')
        if es_ajax:
            return JsonResponse({'success': True})
        return redirect('panel:promodia_lista')

    resumen = []
    for promo in promos_qs:
        total_pagos = Pago.objects.filter(promo_dia=promo).count()
        resumen.append({
            'promo': promo,
            'total_pagos': total_pagos,
        })

    if es_ajax:
        lineas = [
            f'{item["promo"].nombre}: {item["total_pagos"]} pago(s) quedarían sin promoción asociada'
            for item in resumen
        ]
        return JsonResponse({
            'lineas': lineas,
            'advertencia': ('La promoción no se borra en cascada: los pagos que la '
                             'usaron quedan sin promoción asociada, no se eliminan.'),
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
# ESTADÍSTICAS DE CUPONES
# ============================================================
# modificado (T14 - reorg Dashboard): esta vista se retiró. Todo lo que
# mostraba (stats de usos/descuento, cupones más usados, activos sin uso)
# se mudó a Dashboard > Promociones (ver
# panel/views/dashboard.py::_cupones_stats_ventanas y
# dashboard_promociones). El botón "USOS" de cupones/lista.html ahora
# apunta directo a esa página en vez de acá.

