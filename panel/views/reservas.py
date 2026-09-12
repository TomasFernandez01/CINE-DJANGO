from django.contrib import messages
from django.db.models import Q, Sum, Avg, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.dateparse import parse_date
from reservas.models import Reserva
from ..decorators import staff_required, get_sede_activa_panel, get_sede_staff
from ..forms import (
    ReservaForm,
)


def _filtro_sede(request):
    sede_fija = get_sede_staff(request.user)
    return {'funcion__sala__sede': sede_fija} if sede_fija is not None else {}


# ============================================================
# RESERVAS & ANALÍTICA DE OPERACIONES
# ============================================================

@staff_required
def reservas_lista(request):
    estado = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')
    fecha_desde_raw = request.GET.get('fecha_desde', '')
    fecha_hasta_raw = request.GET.get('fecha_hasta', '')

    reservas = Reserva.objects.select_related(
        'usuario', 'funcion__pelicula', 'funcion__sala'
    ).order_by('-fecha_reserva')

    sede_activa = get_sede_activa_panel(request)
    if sede_activa:
        reservas = reservas.filter(funcion__sala__sede=sede_activa)

    if estado:
        reservas = reservas.filter(estado=estado)
    if busqueda:
        reservas = reservas.filter(
            Q(codigo_reserva__icontains=busqueda) |
            Q(usuario__username__icontains=busqueda) |
            Q(funcion__pelicula__titulo__icontains=busqueda)
        )

    # Filtros por Rango de Fechas
    fecha_desde = parse_date(fecha_desde_raw) if fecha_desde_raw else None
    fecha_hasta = parse_date(fecha_hasta_raw) if fecha_hasta_raw else None

    if fecha_desde:
        reservas = reservas.filter(fecha_reserva__date__gte=fecha_desde)
    if fecha_hasta:
        reservas = reservas.filter(fecha_reserva__date__lte=fecha_hasta)

    # METRICAS DE OPERACION & FUNNEL DE CONVERSION
    reservas_confirmadas = reservas.filter(estado='confirmada')
    # modificado: 'total' es un método Python del modelo Reserva, no un campo de BD;
    # no se puede usar en Sum(). El monto real pagado vive en Pago.monto (OneToOne
    # related_name='pago'). Causaba FieldError "Unsupported lookup 'total'...".
    total_ingresos = reservas_confirmadas.aggregate(total=Sum('pago__monto'))['total'] or 0  # modificado
    cantidad_confirmadas = reservas_confirmadas.count()
    ticket_promedio_atv = (total_ingresos / cantidad_confirmadas) if cantidad_confirmadas > 0 else 0

    funnel_stats = reservas.values('estado').annotate(total=Count('id'))
    funnel_dict = {item['estado']: item['total'] for item in funnel_stats}

    contexto = {
        'reservas': reservas[:80],
        'estado': estado,
        'busqueda': busqueda,
        'fecha_desde': fecha_desde_raw,
        'fecha_hasta': fecha_hasta_raw,
        'total': reservas.count(),
        'total_ingresos': total_ingresos,
        'ticket_promedio_atv': ticket_promedio_atv,
        'funnel_dict': funnel_dict,
        'cantidad_confirmadas': cantidad_confirmadas,
        'estados': Reserva.ESTADO_CHOICES,
        'es_super': request.user.is_superuser,
        'seccion_activa': 'reservas',
    }
    return render(request, 'panel/reservas/lista.html', contexto)


@staff_required
def reservas_detalle(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, **_filtro_sede(request))
    pago = getattr(reserva, 'pago', None)

    contexto = {
        'reserva': reserva,
        'pago': pago,
        'seccion_activa': 'reservas',
    }
    return render(request, 'panel/reservas/detalle.html', contexto)


@staff_required
def reservas_editar(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, **_filtro_sede(request))

    if request.method == 'POST':
        form = ReservaForm(request.POST, instance=reserva)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Reserva {reserva.codigo_reserva} actualizada.'
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


