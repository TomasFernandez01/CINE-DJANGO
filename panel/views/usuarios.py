# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from django.shortcuts import render, redirect, get_object_or_404
from pagos.models import Pago
from ..decorators import superuser_required
from ..forms import (
    CrearUsuarioForm,
    EditarUsuarioForm,
)


# ============================================================
# USUARIOS — CRUD (solo superuser)
# ============================================================

@superuser_required
def usuarios_crear(request):
    if request.method == 'POST':
        form = CrearUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'✅ Usuario "{user.username}" creado.')
            return redirect('panel:usuarios_detalle', usuario_id=user.id)
    else:
        form = CrearUsuarioForm()

    return render(request, 'panel/usuarios/form.html', {
        'form': form,
        'titulo_pagina': 'Crear Usuario',
        'accion': 'crear',
        'seccion_activa': 'usuarios',
    })


@superuser_required
def usuarios_editar(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)

    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Usuario "{usuario.username}" actualizado.')
            return redirect('panel:usuarios_detalle', usuario_id=usuario.id)
    else:
        form = EditarUsuarioForm(instance=usuario)

    return render(request, 'panel/usuarios/form.html', {
        'form': form,
        'objeto': usuario,
        'titulo_pagina': f'Editar: {usuario.username}',
        'accion': 'editar',
        'seccion_activa': 'usuarios',
    })
                                                                # V2
# ============================================================
# USUARIOS (solo superuser)
# ============================================================

@superuser_required
def usuarios_lista(request):
    busqueda = request.GET.get('q', '')
    tipo = request.GET.get('tipo', '')

    usuarios = User.objects.select_related('perfil').order_by('-date_joined')

    if busqueda:
        usuarios = usuarios.filter(
            Q(username__icontains=busqueda) |
            Q(email__icontains=busqueda) |
            Q(first_name__icontains=busqueda) |
            Q(last_name__icontains=busqueda)
        )
    if tipo == 'staff':
        usuarios = usuarios.filter(is_staff=True)
    elif tipo == 'superuser':
        usuarios = usuarios.filter(is_superuser=True)
    elif tipo == 'normales':
        usuarios = usuarios.filter(is_staff=False, is_superuser=False)

    contexto = {
        'usuarios': usuarios,
        'busqueda': busqueda,
        'tipo': tipo,
        'total': usuarios.count(),
        'seccion_activa': 'usuarios',
    }
    return render(request, 'panel/usuarios/lista.html', contexto)


@superuser_required
def usuarios_detalle(request, usuario_id):
    usuario = get_object_or_404(User, id=usuario_id)
    reservas = usuario.reservas.select_related(
        'funcion__pelicula', 'funcion__sala'
    ).order_by('-fecha_reserva')[:10]

    total_gastado = Pago.objects.filter(
        reserva__usuario=usuario,
        estado='aprobado'
    ).aggregate(t=Sum('monto'))['t'] or 0

    contexto = {
        'usuario_detalle': usuario,
        'reservas': reservas,
        'total_gastado': total_gastado,
        'total_reservas': usuario.reservas.count(),
        'seccion_activa': 'usuarios',
    }
    return render(request, 'panel/usuarios/detalle.html', contexto)


