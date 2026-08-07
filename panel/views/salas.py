# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from datetime import timedelta
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from reservas.models import Reserva
from salas.models import Sala, Funcion, AsientoBloqueado, CategoriaAsiento
from ..decorators import staff_required
from ..forms import (
    SalaForm,
    SeccionSalaFormSet,
)


# ============================================================
# SALAS — CRUD
# ============================================================
@staff_required
def salas_crear(request):
    if request.method == 'POST':
        form = SalaForm(request.POST)
        if form.is_valid():
            sala_temp = form.save(commit=False)
            formset = SeccionSalaFormSet(request.POST, instance=sala_temp)

            if formset.is_valid():
                sala_temp.save()
                formset.save()
                messages.success(request, f'✅ Sala "{sala_temp.nombre}" creada.')
                if request.POST.get('guardar_y_agregar_otro'):
                    return redirect('panel:salas_crear')
                return redirect('panel:salas_lista')
        else:
            formset = SeccionSalaFormSet(request.POST, instance=Sala())
    else:
        form = SalaForm()
        formset = SeccionSalaFormSet(instance=Sala())

    return render(request, 'panel/salas/form.html', {
        'form': form,
        'formset': formset,
        'titulo_pagina': 'Agregar Sala',
        'accion': 'crear',
        'seccion_activa': 'salas',
    })

@staff_required
def salas_editar(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)

    if request.method == 'POST':
        form = SalaForm(request.POST, instance=sala)
        if form.is_valid():
            sala_temp = form.save(commit=False)
            formset = SeccionSalaFormSet(request.POST, instance=sala_temp)

            if formset.is_valid():
                sala_temp.save()
                formset.save()
                messages.success(request, f'✅ Sala "{sala_temp.nombre}" actualizada.')
                if request.POST.get('guardar_y_agregar_otro'):
                    return redirect('panel:salas_crear')
                return redirect('panel:salas_lista')
        else:
            formset = SeccionSalaFormSet(request.POST, instance=sala)
    else:
        form = SalaForm(instance=sala)
        formset = SeccionSalaFormSet(instance=sala)

    return render(request, 'panel/salas/form.html', {
        'form': form,
        'formset': formset,
        'objeto': sala,
        'titulo_pagina': f'Editar sala: {sala.nombre}',
        'accion': 'editar',
        'seccion_activa': 'salas',
    })

@staff_required
@require_POST
def salas_eliminar(request):
    """
    Borrado múltiple de salas, en dos pasos:
      1. Sin 'confirmado': muestra una vista previa con cuántas funciones y
         reservas se van a borrar en cascada (Sala -> Funcion -> Reserva).
      2. Con 'confirmado=1': borra de verdad.
    """
    ids = request.POST.getlist('seleccionadas')
    if not ids:
        messages.error(request, 'No seleccionaste ninguna sala.')
        return redirect('panel:salas_lista')

    salas_qs = Sala.objects.filter(id__in=ids)
    if not salas_qs.exists():
        messages.error(request, 'Las salas seleccionadas ya no existen.')
        return redirect('panel:salas_lista')

    if request.POST.get('confirmado') == '1':
        nombres = list(salas_qs.values_list('nombre', flat=True))
        salas_qs.delete()  # cascada: borra también sus funciones y reservas
        messages.success(request, f'🗑️ Sala(s) eliminada(s): {", ".join(nombres)}.')
        return redirect('panel:salas_lista')

    # Paso 1: vista previa de lo que se va a borrar en cascada
    resumen = []
    for sala in salas_qs:
        total_funciones = sala.funciones.count()
        total_reservas = Reserva.objects.filter(funcion__sala=sala).count()
        resumen.append({
            'sala': sala,
            'total_funciones': total_funciones,
            'total_reservas': total_reservas,
        })

    return render(request, 'panel/salas/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
        'seccion_activa': 'salas',
    })

@staff_required
def salas_asientos(request, sala_id):
    """
    Mapa visual de la sala para que el staff bloquee/desbloquee asientos
    con un clic. Tiene dos "modos":
      - Permanente (sin función): afecta a la sala para siempre.
      - Una función puntual: afecta solo a esa función (además de lo
        permanente, que siempre se hereda).
    """
    sala = get_object_or_404(Sala, id=sala_id)

    funcion_id = request.GET.get('funcion', '')
    funcion_seleccionada = None
    if funcion_id:
        funcion_seleccionada = get_object_or_404(Funcion, id=funcion_id, sala=sala)

    # Bloqueos aplicables al modo actual
    if funcion_seleccionada:
        bloqueos = sala.bloqueos_asientos.filter(
            Q(funcion__isnull=True) | Q(funcion=funcion_seleccionada)
        )
    else:
        bloqueos = sala.bloqueos_asientos.filter(funcion__isnull=True)

    bloqueos_por_codigo = {b.asiento_codigo: b for b in bloqueos}

    # Todos los bloqueos de la sala (para el listado inferior, sin importar el modo actual)
    todos_los_bloqueos = sala.bloqueos_asientos.select_related('funcion__pelicula').order_by('asiento_codigo')

    funciones_sala = sala.funciones.filter(
        fecha_hora__gte=timezone.now()
    ).select_related('pelicula').order_by('fecha_hora')[:30]

    # Si hay una función seleccionada, mostramos también qué asientos ya
    # están vendidos/reservados (informativo, no se pueden bloquear desde acá).
    asientos_ocupados_reserva = []
    if funcion_seleccionada:
        asientos_ocupados_reserva = funcion_seleccionada.asientos_ocupados()

    # Categorías especiales (ej: "Mejorado") — siempre permanentes por sala,
    # no dependen de la función seleccionada en el modo de arriba.
    categorias = sala.categorias_asientos.all().order_by('asiento_codigo')
    categorias_por_codigo = {c.asiento_codigo: c for c in categorias}

    contexto = {
        'sala': sala,
        'layout': sala.layout_asientos(),
        'bloqueos_por_codigo': bloqueos_por_codigo,
        'todos_los_bloqueos': todos_los_bloqueos,
        'categorias_por_codigo': categorias_por_codigo,
        'todas_las_categorias': categorias,
        'funcion_seleccionada': funcion_seleccionada,
        'funciones_sala': funciones_sala,
        'asientos_ocupados_reserva': asientos_ocupados_reserva,
        'motivo_choices': AsientoBloqueado.MOTIVO_CHOICES,
        'seccion_activa': 'salas',
    }
    return render(request, 'panel/salas/asientos.html', contexto)


# MODIFICACION GEMINI: Endpoint AJAX adaptado para bloqueo masivo (admite codigos separados por comas)
@staff_required
@require_POST
def salas_asientos_bloquear(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)

    asiento_codigo_raw = request.POST.get('asiento_codigo', '').strip()
    motivo = request.POST.get('motivo', 'admin')
    nota = request.POST.get('nota', '').strip()
    funcion_id = request.POST.get('funcion_id') or None

    funcion = None
    if funcion_id:
        funcion = get_object_or_404(Funcion, id=funcion_id, sala=sala)

    # Separar codigos por comas
    codigos = [c.strip() for c in asiento_codigo_raw.split(',') if c.strip()]
    if not codigos:
        return JsonResponse({'success': False, 'errors': {'asiento_codigo': ['Debe indicar al menos un asiento.']}}, status=400)

    bloqueados_data = []
    for codigo in codigos:
        # Evitar duplicar bloqueo si ya existe para esta funcion o permanente
        existente = AsientoBloqueado.objects.filter(sala=sala, asiento_codigo=codigo, funcion=funcion).first()
        if existente:
            continue
            
        bloqueo = AsientoBloqueado(
            sala=sala,
            asiento_codigo=codigo,
            motivo=motivo,
            nota=nota,
            funcion=funcion,
        )
        try:
            bloqueo.full_clean()
            bloqueo.save(skip_validation=True)
            bloqueados_data.append({
                'bloqueo_id': bloqueo.id,
                'asiento_codigo': bloqueo.asiento_codigo,
                'motivo': bloqueo.motivo,
                'motivo_display': bloqueo.get_motivo_display(),
                'nota': bloqueo.nota,
                'permanente': bloqueo.funcion_id is None,
            })
        except ValidationError as e:
            # Si uno falla, seguimos con los demas, o devolvemos error si fue el unico
            if len(codigos) == 1:
                errores = e.message_dict if hasattr(e, 'message_dict') else {'__all__': e.messages}
                return JsonResponse({'success': False, 'errors': errores}, status=400)

    return JsonResponse({
        'success': True,
        'bloqueados': bloqueados_data,
        'asiento_codigo': asiento_codigo_raw  # compatibilidad con JS antiguo
    })

@staff_required
@require_POST
def salas_asientos_desbloquear(request, sala_id):
    """Endpoint AJAX: elimina un bloqueo existente."""
    sala = get_object_or_404(Sala, id=sala_id)
    bloqueo_id = request.POST.get('bloqueo_id')

    bloqueo = get_object_or_404(AsientoBloqueado, id=bloqueo_id, sala=sala)
    asiento_codigo = bloqueo.asiento_codigo
    bloqueo.delete()

    return JsonResponse({'success': True, 'asiento_codigo': asiento_codigo})

# MODIFICACION GEMINI: Endpoint AJAX adaptado para categorizacion masiva (admite codigos separados por comas)

@staff_required
@require_POST
def salas_categoria_asignar(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)

    asiento_codigo_raw = request.POST.get('asiento_codigo', '').strip()
    nombre = request.POST.get('nombre', 'Mejorado').strip() or 'Mejorado'
    multiplicador = request.POST.get('multiplicador', '1.25').strip()
    color = request.POST.get('color', '#f1c40f').strip()

    # Separar codigos por comas
    codigos = [c.strip() for c in asiento_codigo_raw.split(',') if c.strip()]
    if not codigos:
        return JsonResponse({'success': False, 'errors': {'asiento_codigo': ['Debe indicar al menos un asiento.']}}, status=400)

    categorias_data = []
    for codigo in codigos:
        # Si ya existe una categoría para ese asiento, la actualizamos
        categoria = CategoriaAsiento.objects.filter(sala=sala, asiento_codigo=codigo).first()
        if categoria is None:
            categoria = CategoriaAsiento(sala=sala, asiento_codigo=codigo)

        categoria.nombre = nombre
        categoria.multiplicador = multiplicador or '1.25'
        categoria.color = color or '#f1c40f'

        try:
            categoria.full_clean()
            categoria.save(skip_validation=True)
            categorias_data.append({
                'categoria_id': categoria.id,
                'asiento_codigo': categoria.asiento_codigo,
                'nombre': categoria.nombre,
                'multiplicador': str(categoria.multiplicador),
                'color': categoria.color,
            })
        except ValidationError as e:
            if len(codigos) == 1:
                errores = e.message_dict if hasattr(e, 'message_dict') else {'__all__': e.messages}
                return JsonResponse({'success': False, 'errors': errores}, status=400)

    return JsonResponse({
        'success': True,
        'categorias': categorias_data,
        'asiento_codigo': asiento_codigo_raw  # compatibilidad con JS antiguo
    })

@staff_required
@require_POST
def salas_categoria_quitar(request, sala_id):
    """Endpoint AJAX: elimina la categoría especial de un asiento."""
    sala = get_object_or_404(Sala, id=sala_id)
    categoria_id = request.POST.get('categoria_id')

    categoria = get_object_or_404(CategoriaAsiento, id=categoria_id, sala=sala)
    asiento_codigo = categoria.asiento_codigo
    categoria.delete()

    return JsonResponse({'success': True, 'asiento_codigo': asiento_codigo})

# ============================================================
# SALAS
# ============================================================

@staff_required
def salas_lista(request):
    salas = Sala.objects.all().order_by('nombre')
    ahora = timezone.now()

    salas_con_info = []
    for sala in salas:
        funciones_hoy = sala.funciones.filter(
            fecha_hora__gte=ahora.replace(hour=0, minute=0, second=0),
            fecha_hora__lt=ahora.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        ).count()
        salas_con_info.append({
            'sala': sala,
            'funciones_hoy': funciones_hoy,
        })

    contexto = {
        'salas_con_info': salas_con_info,
        'seccion_activa': 'salas',
    }
    return render(request, 'panel/salas/lista.html', contexto)


