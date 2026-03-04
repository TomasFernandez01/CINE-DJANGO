from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Reserva
from salas.models import Funcion

@login_required
def crear_reserva(request, funcion_id):
    funcion = get_object_or_404(Funcion, id=funcion_id, disponible=True)
    
    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad_entradas', 1))
        
        # Verificar que hay asientos disponibles
        if cantidad > funcion.asientos_disponibles():
            messages.error(request, 'No hay suficientes asientos disponibles.')
            return redirect('salas:lista_funciones')
        
        # Crear la reserva
        reserva = Reserva.objects.create(
            usuario=request.user,
            funcion=funcion,
            cantidad_entradas=cantidad
        )
        
        messages.success(request, f'Reserva creada exitosamente. Código: {reserva.codigo_reserva}')
        return redirect('reservas:detalle_reserva', reserva_id=reserva.id)
    
    contexto = {
        'funcion': funcion,
        'asientos_disponibles': funcion.asientos_disponibles(),
    }
    return render(request, 'reservas/crear_reserva.html', contexto)

@login_required
def mis_reservas(request):
    # Filtro para mostrar/ocultar canceladas
    mostrar_canceladas = request.GET.get('mostrar_canceladas', 'si')
    
    if mostrar_canceladas == 'no':
        reservas = Reserva.objects.filter(usuario=request.user).exclude(estado='cancelada').select_related('funcion__pelicula', 'funcion__sala')
    else:
        reservas = Reserva.objects.filter(usuario=request.user).select_related('funcion__pelicula', 'funcion__sala')
    
    contexto = {
        'reservas': reservas,
        'mostrar_canceladas': mostrar_canceladas,
    }
    return render(request, 'reservas/mis_reservas.html', contexto)

@login_required
def detalle_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    contexto = {
        'reserva': reserva
    }
    return render(request, 'reservas/detalle_reserva.html', contexto)

@login_required
def cancelar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    
    if reserva.estado == 'pendiente':
        reserva.estado = 'cancelada'
        reserva.save()
        messages.success(request, 'Reserva cancelada exitosamente.')
    else:
        messages.error(request, 'No se puede cancelar esta reserva.')
    
    return redirect('reservas:mis_reservas')

@login_required
def eliminar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    
    # Solo permitir eliminar reservas canceladas
    if reserva.estado == 'cancelada':
        codigo = reserva.codigo_reserva
        reserva.delete()
        messages.success(request, f'Reserva {codigo} eliminada del historial.')
    else:
        messages.error(request, 'Solo se pueden eliminar reservas canceladas.')
    
    return redirect('reservas:mis_reservas')