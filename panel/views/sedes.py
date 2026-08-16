# nuevo (Sedes - Fase 3): CRUD de Sede dentro del Panel. Mismo patrón que
# panel/views/promociones.py::promodia_* (lista con checkboxes + borrado
# múltiple en 2 pasos + form simple sin formset).
#
# Restringido a @superuser_required (no @staff_required): crear/editar/
# borrar sedes es una decisión estructural de toda la cadena, no algo
# que un staff de una sola sede debería poder tocar.

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from sedes.models import Sede
from salas.models import Sala
from reservas.models import Reserva
from ..decorators import superuser_required, staff_required, get_sede_staff
from ..forms import SedeForm


@staff_required
@require_POST
def cambiar_sede_panel(request):
    """
    nuevo (Sedes - Fase 3): guarda la sede "enfocada" en el Panel
    (session['panel_sede_id']), para quien puede ver todas las sedes
    (superuser, o staff sin sede_administrada fija) y quiere navegar
    Salas/Funciones/Reservas/Pagos/Dashboard centrado en una sola.

    A diferencia de sedes:cambiar_sede (lado cliente), esto NO cancela
    ninguna reserva — es solo un filtro de visualización del staff, no
    afecta ninguna compra en curso de ningún cliente.

    Si el usuario está restringido a una sede fija (perfil.sede_administrada),
    este selector no debería ni mostrarse en el template — pero por las
    dudas, si igual llega el POST, se ignora silenciosamente.
    """
    if get_sede_staff(request.user) is not None:
        return redirect(request.POST.get('next') or 'panel:inicio')

    sede_id = request.POST.get('sede_id') or None
    if sede_id:
        sede = get_object_or_404(Sede, id=sede_id, activa=True)
        request.session['panel_sede_id'] = sede.id
        messages.success(request, f'📍 Panel enfocado en: {sede.nombre}.')
    else:
        request.session.pop('panel_sede_id', None)
        messages.info(request, 'Panel mostrando todas las sedes.')

    return redirect(request.POST.get('next') or 'panel:inicio')


@superuser_required
def sedes_lista(request):
    sedes = Sede.objects.all().order_by('nombre')
    return render(request, 'panel/sedes/lista.html', {
        'sedes': sedes,
        'seccion_activa': 'sedes',
    })


@superuser_required
def sedes_crear(request):
    if request.method == 'POST':
        form = SedeForm(request.POST)
        if form.is_valid():
            sede = form.save()
            messages.success(request, f'✅ Sede "{sede.nombre}" creada.')
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:sedes_crear')
            return redirect('panel:sedes_lista')
    else:
        form = SedeForm()

    return render(request, 'panel/sedes/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Sede',
        'accion': 'crear',
        'seccion_activa': 'sedes',
    })


@superuser_required
def sedes_editar(request, sede_id):
    sede = get_object_or_404(Sede, id=sede_id)

    if request.method == 'POST':
        form = SedeForm(request.POST, instance=sede)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Sede "{sede.nombre}" actualizada.')
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:sedes_crear')
            return redirect('panel:sedes_lista')
    else:
        form = SedeForm(instance=sede)

    return render(request, 'panel/sedes/form.html', {
        'form': form,
        'objeto': sede,
        'titulo_pagina': f'Editar sede: {sede.nombre}',
        'accion': 'editar',
        'seccion_activa': 'sedes',
    })


@superuser_required
@require_POST
def sedes_eliminar(request):
    """
    Borrado múltiple de sedes, en dos pasos (mismo patrón que
    salas_eliminar/promodia_eliminar).

    IMPORTANTE: Sala.sede es on_delete=PROTECT (ver salas/models.py) —
    Django va a impedir borrar una Sede que todavía tenga salas
    asociadas. En vez de dejar que reviente con un ProtectedError feo,
    se lo mostramos al staff ANTES, en la vista previa, y se bloquea el
    botón de confirmar si hay salas dependientes.
    """
    ids = request.POST.getlist('seleccionadas')
    if not ids:
        messages.error(request, 'No seleccionaste ninguna sede.')
        return redirect('panel:sedes_lista')

    sedes_qs = Sede.objects.filter(id__in=ids)
    if not sedes_qs.exists():
        messages.error(request, 'Las sedes seleccionadas ya no existen.')
        return redirect('panel:sedes_lista')

    if request.POST.get('confirmado') == '1':
        # Recalculamos acá también (no solo confiar en el JS del template)
        # por si alguna sala se creó justo en el medio.
        if Sala.objects.filter(sede__in=sedes_qs).exists():
            messages.error(
                request,
                'No se puede eliminar: alguna de las sedes seleccionadas todavía tiene salas asociadas. '
                'Movés o borrás esas salas primero.'
            )
            return redirect('panel:sedes_lista')
        nombres = list(sedes_qs.values_list('nombre', flat=True))
        sedes_qs.delete()
        messages.success(request, f'🗑️ Sede(s) eliminada(s): {", ".join(nombres)}.')
        return redirect('panel:sedes_lista')

    # Paso 1: vista previa
    resumen = []
    for sede in sedes_qs:
        total_salas = Sala.objects.filter(sede=sede).count()
        total_reservas = Reserva.objects.filter(funcion__sala__sede=sede).count()
        resumen.append({
            'sede': sede,
            'total_salas': total_salas,
            'total_reservas': total_reservas,
            'bloqueado': total_salas > 0,
        })

    return render(request, 'panel/sedes/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
        'hay_bloqueadas': any(r['bloqueado'] for r in resumen),
        'seccion_activa': 'sedes',
    })
