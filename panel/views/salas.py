# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from datetime import timedelta
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from reservas.models import Reserva
from salas.models import Sala, Funcion, AsientoBloqueado, CategoriaAsiento
from ..decorators import staff_required, get_sede_activa_panel, get_sede_staff, superuser_required
from ..forms import (
    SalaForm,
    SeccionSalaFormSet,
)


def _filtro_sede(request):
    """
    nuevo (Sedes - Fase 3): dict listo para pasar a get_object_or_404 /
    filter — {'sede': sede_fija} si el staff está restringido, {} (sin
    filtrar) si puede ver todas. Evita repetir el if en cada vista de
    este archivo.
    """
    sede_fija = get_sede_staff(request.user)
    return {'sede': sede_fija} if sede_fija is not None else {}


# ============================================================
# SALAS — CRUD
# ============================================================
# MODIFICACION GEMINI: Crear salas es función exclusiva del SuperUser (Corporate HQ)
@superuser_required
def salas_crear(request):
    sede_fija = get_sede_staff(request.user)
    if request.method == 'POST':
        form = SalaForm(request.POST, sede_fija=sede_fija)
        if form.is_valid():
            sala_temp = form.save(commit=False)
            formset = SeccionSalaFormSet(request.POST, instance=sala_temp)

            if formset.is_valid():
                sala_temp.save()
                formset.save()
                messages.success(request, f'Sala "{sala_temp.nombre}" creada.')
                if request.POST.get('guardar_y_agregar_otro'):
                    return redirect('panel:salas_crear')
                return redirect('panel:salas_lista')
        else:
            formset = SeccionSalaFormSet(request.POST, instance=Sala())
    else:
        form = SalaForm(sede_fija=sede_fija)
        formset = SeccionSalaFormSet(instance=Sala())

    return render(request, 'panel/salas/form.html', {
        'form': form,
        'formset': formset,
        'sede_fija': sede_fija,
        'titulo_pagina': 'Agregar Sala',
        'accion': 'crear',
        'seccion_activa': 'salas',
    })

@staff_required
def salas_editar(request, sala_id):
    sede_fija = get_sede_staff(request.user)
    filtro_sala = {'id': sala_id}
    if sede_fija is not None:
        filtro_sala['sede'] = sede_fija
    sala = get_object_or_404(Sala, **filtro_sala)
    es_super = request.user.is_superuser  # modificado (T1)

    if request.method == 'POST':
        form = SalaForm(request.POST, instance=sala, sede_fija=sede_fija)
        if form.is_valid():
            sala_temp = form.save(commit=False)

            # modificado (T1): Staff (no SuperUser) solo puede activar/
            # desactivar la sala. No puede cambiar sede, nombre, tecnología
            # (tipo), capacidad (filas/columnas) ni el multiplicador de
            # precio -- esos campos quedan reservados a SuperUser (mismo
            # patrón que panel/views/peliculas.py::peliculas_editar). Tampoco
            # se toca el formset de secciones (estructura física de la sala).
            if not es_super:
                original = Sala.objects.get(id=sala.id)
                sala_temp.sede = original.sede
                sala_temp.nombre = original.nombre
                sala_temp.tipo = original.tipo
                sala_temp.filas = original.filas
                sala_temp.columnas = original.columnas
                sala_temp.multiplicador_precio = original.multiplicador_precio
                sala_temp.save()
                messages.success(request, f'Sala "{sala_temp.nombre}" actualizada (disponibilidad por Staff).')
                return redirect('panel:salas_lista')

            formset = SeccionSalaFormSet(request.POST, instance=sala_temp)
            if formset.is_valid():
                sala_temp.save()
                formset.save()
                messages.success(request, f'Sala "{sala_temp.nombre}" actualizada.')
                if request.POST.get('guardar_y_agregar_otro'):
                    return redirect('panel:salas_crear')
                return redirect('panel:salas_lista')
        else:
            formset = SeccionSalaFormSet(request.POST, instance=sala)
    else:
        form = SalaForm(instance=sala, sede_fija=sede_fija)
        formset = SeccionSalaFormSet(instance=sala)

    return render(request, 'panel/salas/form.html', {
        'form': form,
        'formset': formset,
        'objeto': sala,
        'sede_fija': sede_fija,
        'titulo_pagina': f'Editar sala: {sala.nombre}',
        'accion': 'editar',
        'seccion_activa': 'salas',
        'es_super': es_super,
    })

# MODIFICACION GEMINI: Eliminación de salas exclusiva para SuperUser
@superuser_required
@require_POST
def salas_eliminar(request):
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    ids = request.POST.getlist('seleccionadas')
    if not ids:
        if es_ajax:
            return JsonResponse({'error': 'No seleccionaste ninguna sala.'}, status=400)
        messages.error(request, 'No seleccionaste ninguna sala.')
        return redirect('panel:salas_lista')

    salas_qs = Sala.objects.filter(id__in=ids)
    sede_fija = get_sede_staff(request.user)
    if sede_fija is not None:
        salas_qs = salas_qs.filter(sede=sede_fija)
    if not salas_qs.exists():
        if es_ajax:
            return JsonResponse({'error': 'Las salas seleccionadas ya no existen.'}, status=400)
        messages.error(request, 'Las salas seleccionadas ya no existen.')
        return redirect('panel:salas_lista')

    if request.POST.get('confirmado') == '1':
        nombres = list(salas_qs.values_list('nombre', flat=True))
        salas_qs.delete()
        messages.success(request, f'Sala(s) eliminada(s): {", ".join(nombres)}.')
        if es_ajax:
            return JsonResponse({'success': True})
        return redirect('panel:salas_lista')

    resumen = []
    for sala in salas_qs:
        total_funciones = sala.funciones.count()
        total_reservas = Reserva.objects.filter(funcion__sala=sala).count()
        resumen.append({
            'sala': sala,
            'total_funciones': total_funciones,
            'total_reservas': total_reservas,
        })

    if es_ajax:
        lineas = [
            f'{item["sala"].nombre}: {item["total_funciones"]} función(es), '
            f'{item["total_reservas"]} reserva(s)'
            for item in resumen
        ]
        return JsonResponse({
            'lineas': lineas,
            'advertencia': ('Esta acción no se puede deshacer. Al borrar una sala, '
                             'también se borran en cascada todas sus funciones y las '
                             'reservas asociadas a esas funciones.'),
        })

    return render(request, 'panel/salas/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
        'seccion_activa': 'salas',
    })

@staff_required
def salas_asientos(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id, **_filtro_sede(request))

    funcion_id = request.GET.get('funcion', '')
    funcion_seleccionada = None
    if funcion_id:
        funcion_seleccionada = get_object_or_404(Funcion, id=funcion_id, sala=sala)

    if funcion_seleccionada:
        bloqueos = sala.bloqueos_asientos.filter(
            Q(funcion__isnull=True) | Q(funcion=funcion_seleccionada)
        )
    else:
        bloqueos = sala.bloqueos_asientos.filter(funcion__isnull=True)

    bloqueos_por_codigo = {b.asiento_codigo: b for b in bloqueos}
    todos_los_bloqueos = sala.bloqueos_asientos.select_related('funcion__pelicula').order_by('asiento_codigo')

    funciones_sala = sala.funciones.filter(
        fecha_hora__gte=timezone.now()
    ).select_related('pelicula').order_by('fecha_hora')[:30]

    asientos_ocupados_reserva = []
    if funcion_seleccionada:
        asientos_ocupados_reserva = funcion_seleccionada.asientos_ocupados()

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


@staff_required
@require_POST
def salas_asientos_bloquear(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id, **_filtro_sede(request))

    asiento_codigo_raw = request.POST.get('asiento_codigo', '').strip()
    motivo = request.POST.get('motivo', 'admin')
    nota = request.POST.get('nota', '').strip()
    funcion_id = request.POST.get('funcion_id') or None

    funcion = None
    if funcion_id:
        funcion = get_object_or_404(Funcion, id=funcion_id, sala=sala)

    codigos = [c.strip() for c in asiento_codigo_raw.split(',') if c.strip()]
    if not codigos:
        return JsonResponse({'success': False, 'errors': {'asiento_codigo': ['Debe indicar al menos un asiento.']}}, status=400)

    bloqueados_data = []
    for codigo in codigos:
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
            if len(codigos) == 1:
                errores = e.message_dict if hasattr(e, 'message_dict') else {'__all__': e.messages}
                return JsonResponse({'success': False, 'errors': errores}, status=400)

    return JsonResponse({
        'success': True,
        'bloqueados': bloqueados_data,
        'asiento_codigo': asiento_codigo_raw
    })

@staff_required
@require_POST
def salas_asientos_desbloquear(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id, **_filtro_sede(request))
    bloqueo_id = request.POST.get('bloqueo_id')

    bloqueo = get_object_or_404(AsientoBloqueado, id=bloqueo_id, sala=sala)
    asiento_codigo = bloqueo.asiento_codigo
    bloqueo.delete()

    return JsonResponse({'success': True, 'asiento_codigo': asiento_codigo})


@staff_required
@require_POST
def salas_categoria_asignar(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id, **_filtro_sede(request))

    asiento_codigo_raw = request.POST.get('asiento_codigo', '').strip()
    nombre = request.POST.get('nombre', 'Mejorado').strip() or 'Mejorado'
    multiplicador = request.POST.get('multiplicador', '1.25').strip()
    color = request.POST.get('color', '#f1c40f').strip()

    codigos = [c.strip() for c in asiento_codigo_raw.split(',') if c.strip()]
    if not codigos:
        return JsonResponse({'success': False, 'errors': {'asiento_codigo': ['Debe indicar al menos un asiento.']}}, status=400)

    categorias_data = []
    for codigo in codigos:
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
        'asiento_codigo': asiento_codigo_raw
    })

@staff_required
@require_POST
def salas_categoria_quitar(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id, **_filtro_sede(request))
    categoria_id = request.POST.get('categoria_id')

    categoria = get_object_or_404(CategoriaAsiento, id=categoria_id, sala=sala)
    asiento_codigo = categoria.asiento_codigo
    categoria.delete()

    return JsonResponse({'success': True, 'asiento_codigo': asiento_codigo})

# ============================================================
# SALAS - LISTA Y ANALÍTICA
# ============================================================

@staff_required
def salas_lista(request):
    salas = Sala.objects.all().order_by('nombre')
    ahora = timezone.now()

    sede_activa = get_sede_activa_panel(request)
    if sede_activa:
        salas = salas.filter(sede=sede_activa)

    salas_con_info = []
    for sala in salas:
        funciones_hoy = sala.funciones.filter(
            fecha_hora__gte=ahora.replace(hour=0, minute=0, second=0),
            fecha_hora__lt=ahora.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        ).count()
        
        # MODIFICACION GEMINI: Métrica de ocupación por sala
        total_reservas_sala = Reserva.objects.filter(funcion__sala=sala, estado='confirmada').count()
        total_entradas_sala = Reserva.objects.filter(funcion__sala=sala, estado='confirmada').aggregate(
            total=Sum('cantidad_entradas')
        )['total'] or 0

        # modificado (T3, corregido): la versión anterior dividía el total
        # HISTÓRICO de entradas vendidas (todas las funciones que tuvo la
        # sala, para siempre) por la capacidad de UNA sola función. Si la
        # sala tenía, por ejemplo, 5 funciones con buena venta, el % podía
        # superar el 100% sin sentido — el numerador sumaba entradas de
        # varias funciones distintas y el denominador solo contaba una vez.
        # La ocupación real de "una sala" no existe como concepto único (una
        # sala puede tener muchas funciones con distinta ocupación cada una);
        # lo que sí tiene sentido es el PROMEDIO de ocupación entre todas sus
        # funciones. Por eso ahora se divide por (capacidad * cantidad de
        # funciones que tuvo esa sala), no por la capacidad de una sola.
        capacidad_total = sala.capacidad or (sala.filas * sala.columnas)
        cantidad_funciones_sala = sala.funciones.count()
        capacidad_acumulada = capacidad_total * cantidad_funciones_sala
        if capacidad_acumulada:
            ocupacion_pct = round((total_entradas_sala / capacidad_acumulada) * 100, 1)
        else:
            ocupacion_pct = 0  # modificado (T3): sin capacidad o sin funciones -> 0%

        salas_con_info.append({
            'sala': sala,
            'funciones_hoy': funciones_hoy,
            'total_reservas_sala': total_reservas_sala,
            'total_entradas_sala': total_entradas_sala,
            'ocupacion_pct': ocupacion_pct,  # modificado (T3)
        })

    contexto = {
        'salas_con_info': salas_con_info,
        'es_super': request.user.is_superuser,
        'seccion_activa': 'salas',
    }
    return render(request, 'panel/salas/lista.html', contexto)


