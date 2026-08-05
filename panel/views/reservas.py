# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from reservas.models import Reserva
from ..decorators import staff_required
from ..forms import (
    ReservaForm,
)


# ============================================================
# RESERVAS
# ============================================================

@staff_required
def reservas_lista(request):
    estado = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')

    reservas = Reserva.objects.select_related(
        'usuario', 'funcion__pelicula', 'funcion__sala'
    ).order_by('-fecha_reserva')

    if estado:
        reservas = reservas.filter(estado=estado)
    if busqueda:
        reservas = reservas.filter(
            Q(codigo_reserva__icontains=busqueda) |
            Q(usuario__username__icontains=busqueda) |
            Q(funcion__pelicula__titulo__icontains=busqueda)
        )

    contexto = {
        'reservas': reservas[:60],
        'estado': estado,
        'busqueda': busqueda,
        'total': reservas.count(),
        'estados': Reserva.ESTADO_CHOICES,
        'seccion_activa': 'reservas',
    }
    return render(request, 'panel/reservas/lista.html', contexto)


@staff_required
def reservas_detalle(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    pago = getattr(reserva, 'pago', None)

    contexto = {
        'reserva': reserva,
        'pago': pago,
        'seccion_activa': 'reservas',
    }
    return render(request, 'panel/reservas/detalle.html', contexto)


# ============================================================

# ============================================================
# AGREGAR AL BLOQUE DE IMPORTS DE panel/views.py:
#   from .forms import (..., ReservaForm)
#
# AGREGAR ESTA VISTA AL FINAL DE LA SECCIÓN "RESERVAS" EN panel/views.py
# ============================================================

@staff_required
def reservas_editar(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)

    if request.method == 'POST':
        form = ReservaForm(request.POST, instance=reserva)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'✅ Reserva {reserva.codigo_reserva} actualizada.'
            )
            return redirect('panel:reservas_detalle', reserva_id=reserva.id)
    else:
        form = ReservaForm(instance=reserva)

    pago = getattr(reserva, 'pago', None)

    return render(request, 'panel/reservas/form.html', {
        'form': form,
        'reserva': reserva,
        'pago': pago,
        'seccion_activa': 'reservas',
    })

