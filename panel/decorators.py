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