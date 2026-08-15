# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from datetime import timedelta
from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from pagos.models import Pago
from salas.models import Sala, Funcion
from ..decorators import staff_required
from ..forms import (
    FuncionForm,
)


# ============================================================
# FUNCIONES — CRUD
# ============================================================

@staff_required
def funciones_crear(request):
    if request.method == 'POST':
        form = FuncionForm(request.POST)
        if form.is_valid():
            try:
                funcion = form.save()
                messages.success(
                    request,
                    f'✅ Función de "{funcion.pelicula.titulo}" creada el '
                    f'{funcion.fecha_hora.strftime("%d/%m/%Y a las %H:%M")}.'
                )
                if request.POST.get('guardar_y_agregar_otro'):
                    return redirect('panel:funciones_crear')
                return redirect('panel:funciones_detalle', funcion_id=funcion.id)
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
    else:
        # Pre-seleccionar pelicula/sala si vienen como parámetros
        initial = {}
        if request.GET.get('pelicula'):
            initial['pelicula'] = request.GET.get('pelicula')
        if request.GET.get('sala'):
            initial['sala'] = request.GET.get('sala')
        form = FuncionForm(initial=initial)

    return render(request, 'panel/funciones/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Función',
        'accion': 'crear',
        'seccion_activa': 'funciones',
    })


@staff_required
def funciones_editar(request, funcion_id):
    funcion = get_object_or_404(Funcion, id=funcion_id)

    if request.method == 'POST':
        form = FuncionForm(request.POST, instance=funcion)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, '✅ Función actualizada.')
                if request.POST.get('guardar_y_agregar_otro'):
                    return redirect('panel:funciones_crear')
                return redirect('panel:funciones_detalle', funcion_id=funcion.id)
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
    else:
        form = FuncionForm(instance=funcion)

    return render(request, 'panel/funciones/form.html', {
        'form': form,
        'objeto': funcion,
        'titulo_pagina': f'Editar: {funcion.pelicula.titulo}',
        'accion': 'editar',
        'seccion_activa': 'funciones',
    })
@staff_required
@require_POST
def funciones_eliminar(request):
    """
    Borrado múltiple de funciones, en dos pasos (mismo patrón que salas_eliminar):
      1. Sin 'confirmado': vista previa con cuántas reservas y pagos se van a
         borrar en cascada (Funcion -> Reserva -> Pago).
      2. Con 'confirmado=1': borra de verdad.
    """
    # modificado: mismo mecanismo que salas_eliminar (ver comentario ahí) -
    # paso 1 responde JSON cuando lo pide static/js/panel/shared/eliminar_modal.js.
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    ids = request.POST.getlist('seleccionadas')
    if not ids:
        if es_ajax:
            return JsonResponse({'error': 'No seleccionaste ninguna función.'}, status=400)
        messages.error(request, 'No seleccionaste ninguna función.')
        return redirect('panel:funciones_lista')

    funciones_qs = Funcion.objects.filter(id__in=ids).select_related('pelicula', 'sala')
    if not funciones_qs.exists():
        if es_ajax:
            return JsonResponse({'error': 'Las funciones seleccionadas ya no existen.'}, status=400)
        messages.error(request, 'Las funciones seleccionadas ya no existen.')
        return redirect('panel:funciones_lista')

    if request.POST.get('confirmado') == '1':
        descripciones = [
            f'{f.pelicula.titulo} ({f.fecha_hora.strftime("%d/%m/%Y %H:%M")})'
            for f in funciones_qs
        ]
        funciones_qs.delete()  # cascada: borra también sus reservas y pagos
        messages.success(request, f'🗑️ Función(es) eliminada(s): {", ".join(descripciones)}.')
        if es_ajax:
            return JsonResponse({'success': True})  # modificado
        return redirect('panel:funciones_lista')

    # Paso 1: vista previa de lo que se va a borrar en cascada
    resumen = []
    for funcion in funciones_qs:
        total_reservas = funcion.reservas.count()
        total_pagos = Pago.objects.filter(reserva__funcion=funcion).count()
        resumen.append({
            'funcion': funcion,
            'total_reservas': total_reservas,
            'total_pagos': total_pagos,
        })

    if es_ajax:
        # modificado
        lineas = [
            f'{item["funcion"].pelicula.titulo} '
            f'({item["funcion"].fecha_hora.strftime("%d/%m/%Y %H:%M")}): '
            f'{item["total_reservas"]} reserva(s), {item["total_pagos"]} pago(s)'
            for item in resumen
        ]
        return JsonResponse({
            'lineas': lineas,
            'advertencia': ('Esta acción no se puede deshacer. Al borrar una función, '
                             'también se borran en cascada sus reservas y los pagos '
                             'asociados.'),
        })

    return render(request, 'panel/funciones/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
        'seccion_activa': 'funciones',
    })

# ============================================================
# FUNCIONES
# ============================================================

@staff_required
def funciones_lista(request):
    ahora = timezone.now()
    filtro = request.GET.get('filtro', 'proximas')

    funciones = Funcion.objects.select_related('pelicula', 'sala').order_by('fecha_hora')

    if filtro == 'hoy':
        hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        funciones = funciones.filter(
            fecha_hora__gte=hoy,
            fecha_hora__lt=hoy + timedelta(days=1)
        )
    elif filtro == 'proximas':
        funciones = funciones.filter(fecha_hora__gte=ahora)
    elif filtro == 'pasadas':
        funciones = funciones.filter(fecha_hora__lt=ahora).order_by('-fecha_hora')
    elif filtro == 'todas':
        funciones = funciones.order_by('-fecha_hora')

    # NUEVO
    filtros_tabs = [
        ('hoy',      '📅 Hoy'),
        ('proximas', '⏭️ Próximas'),
        ('pasadas',  '⏮️ Pasadas'),
        ('todas',    '📋 Todas'),
        ]

    contexto = {
        'funciones': funciones[:50],
        'filtro': filtro,
        'total': funciones.count(),
        'filtros_tabs': filtros_tabs,
        'seccion_activa': 'funciones',
    }
    return render(request, 'panel/funciones/lista.html', contexto)


@staff_required
def funciones_detalle(request, funcion_id):
    funcion = get_object_or_404(Funcion, id=funcion_id)
    reservas = funcion.reservas.select_related(
        'usuario', 'pago'
    ).order_by('-fecha_reserva')

    entradas_vendidas = reservas.filter(
        estado='confirmada'
    ).aggregate(t=Sum('cantidad_entradas'))['t'] or 0

    recaudado = Pago.objects.filter(
        reserva__funcion=funcion,
        estado='aprobado'
    ).aggregate(t=Sum('monto'))['t'] or 0

    qr_escaneados = Pago.objects.filter(
        reserva__funcion=funcion,
        qr_escaneado=True
    ).count()

    contexto = {
        'funcion': funcion,
        'reservas': reservas,
        'entradas_vendidas': entradas_vendidas,
        'capacidad': funcion.sala.capacidad,
        'ocupacion_pct': int(entradas_vendidas / funcion.sala.capacidad * 100) if funcion.sala.capacidad else 0,
        'recaudado': recaudado,
        'qr_escaneados': qr_escaneados,
        'asientos_ocupados': funcion.asientos_ocupados(),
        'layout': funcion.sala.layout_asientos(),
        'seccion_activa': 'funciones',
    }
    return render(request, 'panel/funciones/detalle.html', contexto)

# MODIFICACION GEMINI: Vista para retornar las funciones de una sala en un dia específico y sus tiempos
@staff_required
def funciones_margen_tiempo(request):
    sala_id = request.GET.get('sala_id')
    fecha_str = request.GET.get('fecha')  # Formato YYYY-MM-DD
    
    if not sala_id or not fecha_str:
        return JsonResponse({'error': 'Faltan parámetros'}, status=400)
        
    try:
        sala = Sala.objects.get(id=sala_id)
        from django.utils.dateparse import parse_date
        fecha_date = parse_date(fecha_str)
        if not fecha_date:
            return JsonResponse({'error': 'Fecha inválida'}, status=400)
            
        # Rango completo del dia en la zona horaria actual
        inicio_dia = timezone.make_aware(timezone.datetime.combine(fecha_date, timezone.datetime.min.time()))
        fin_dia = timezone.make_aware(timezone.datetime.combine(fecha_date, timezone.datetime.max.time()))
        
        funciones = Funcion.objects.filter(
            sala=sala,
            fecha_hora__range=(inicio_dia, fin_dia)
        ).select_related('pelicula').order_by('fecha_hora')
        
        funciones_data = []
        for f in funciones:
            fin = f.calcular_hora_fin()
            # Convertir a hora local para mostrar correctamente al admin
            hora_local_inicio = timezone.localtime(f.fecha_hora)
            hora_local_fin = timezone.localtime(fin)
            funciones_data.append({
                'id': f.id,
                'pelicula': f.pelicula.titulo,
                'inicio': hora_local_inicio.strftime('%H:%M'),
                'fin': hora_local_fin.strftime('%H:%M'),
                'duracion': f.pelicula.duracion or 120,
            })
            
        return JsonResponse({
            'funciones': funciones_data,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
