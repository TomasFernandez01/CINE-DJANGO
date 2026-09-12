from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def staff_required(view_func):
    """
    Decorador: requiere is_staff.
    Para empleados del cine (boleteros, supervisores).
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('usuarios:login')
        if not request.user.is_staff:
            messages.error(request, 'No tenés permisos para acceder a esta sección.')
            return redirect('peliculas:inicio')
        return view_func(request, *args, **kwargs)
    return wrapper


def superuser_required(view_func):
    """
    Decorador: requiere is_superuser.
    Para administradores con acceso total.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('usuarios:login')
        if not request.user.is_superuser:
            messages.error(request, 'Esta sección es solo para administradores.')
            return redirect('panel:inicio')
        return view_func(request, *args, **kwargs)
    return wrapper


# nuevo (Sedes - Fase 3)
def get_sede_staff(user):
    """
    Devuelve la Sede a la que está restringido este usuario en el Panel,
    o None si puede ver/administrar TODAS las sedes.

    Reglas (confirmadas): un superuser siempre ve todo, sin excepción,
    aunque su perfil tenga una sede_administrada cargada por error. Un
    staff normal (is_staff, no superuser) queda restringido a
    perfil.sede_administrada — si ese campo está vacío, también ve todo
    (pensado como caso de transición/rol regional, no el default
    esperado para un empleado de una sede puntual).
    """
    if not user.is_authenticated or user.is_superuser:
        return None
    return getattr(getattr(user, 'perfil', None), 'sede_administrada', None)


def get_sede_activa_panel(request):
    """
    Sede por la que hay que filtrar Salas/Funciones/Reservas/Pagos en
    ESTA request del Panel. Combina la restricción dura de
    get_sede_staff() con un selector opcional (guardado en
    session['panel_sede_id'], separado de session['sede_id'] que usa el
    selector del lado cliente — son sesiones para roles distintos del
    mismo usuario) para quien SÍ puede ver todas las sedes pero quiere
    enfocarse en una a la vez al navegar el Panel.

    Devuelve una Sede o None (None = sin filtrar, ve todo).
    """
    sede_fija = get_sede_staff(request.user)
    if sede_fija is not None:
        return sede_fija

    from sedes.models import Sede
    panel_sede_id = request.session.get('panel_sede_id')
    if panel_sede_id:
        return Sede.objects.filter(id=panel_sede_id, activa=True).first()
    return None