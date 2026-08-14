from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Sede

try:
    from utils.email_utils import enviar_email_cancelacion_reserva
    EMAIL_DISPONIBLE = True
except ImportError:
    EMAIL_DISPONIBLE = False


@require_POST
def cambiar_sede(request):
    """
    Cambia la sede activa del cliente (guardada en session['sede_id']).

    Decisión de negocio (confirmada): si el usuario tiene alguna reserva
    en estado 'pendiente' (todavía no pagada) de la sede que está
    dejando, se cancela automáticamente al cambiar — no tiene sentido
    dejarla colgada apuntando a una sede que ya no es la elegida, y esos
    asientos quedarían bloqueados para otros clientes de esa sede hasta
    que expire sola por tiempo.

    No se tocan reservas 'confirmada' (ya pagadas): esas siguen firmes
    sin importar la sede que esté eligiendo el usuario ahora.
    """
    sede_id_nuevo = request.POST.get('sede_id') or None
    sede_id_anterior = request.session.get('sede_id')

    if sede_id_nuevo:
        sede = get_object_or_404(Sede, id=sede_id_nuevo, activa=True)
        request.session['sede_id'] = sede.id
        messages.success(request, f'📍 Ahora estás viendo la sede: {sede.nombre}.')
    else:
        # "Todas las sedes" — vuelve a mostrar todo sin filtrar
        request.session.pop('sede_id', None)
        messages.info(request, 'Mostrando funciones de todas las sedes.')

    sede_id_nuevo_int = int(sede_id_nuevo) if sede_id_nuevo else None
    hubo_cambio_real = sede_id_anterior and sede_id_anterior != sede_id_nuevo_int

    if request.user.is_authenticated and hubo_cambio_real:
        # import acá adentro (no arriba del archivo) para evitar import
        # circular: reservas/models.py no depende de sedes, pero sedes no
        # necesita depender de reservas salvo en este caso puntual.
        from reservas.models import Reserva

        reservas_a_cancelar = list(
            Reserva.objects.filter(
                usuario=request.user,
                estado='pendiente',
                funcion__sala__sede_id=sede_id_anterior,
            )
        )
        for reserva in reservas_a_cancelar:
            reserva.estado = 'cancelada'
            reserva.save(update_fields=['estado'])
            if EMAIL_DISPONIBLE:
                try:
                    enviar_email_cancelacion_reserva(reserva)
                except Exception:
                    pass

        if reservas_a_cancelar:
            messages.warning(
                request,
                '⚠️ Tu reserva pendiente de la sede anterior fue cancelada automáticamente al cambiar de sede.'
            )

    siguiente = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
    return redirect(siguiente)
