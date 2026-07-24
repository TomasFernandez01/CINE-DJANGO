from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from .forms import RegistroForm, EditarPerfilForm
# MODIFICACION DE GEMINI
from peliculas.models import Pelicula
# FIN MODIFICACION DE GEMINI

def registro(request):
    if request.user.is_authenticated:
        return redirect('peliculas:inicio')
    
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Bienvenido {user.first_name}! Tu cuenta ha sido creada exitosamente.')
            return redirect('peliculas:inicio')
    else:
        form = RegistroForm()

    # MODIFICACION DE GEMINI
    peliculas_poster = Pelicula.objects.filter(poster__isnull=False)[:6]
    contexto = {
        'form': form,
        'peliculas_poster': peliculas_poster
    }
    # FIN MODIFICACION DE GEMINI
    return render(request, 'usuarios/registro.html', contexto)

############################################################################

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('panel:inicio')
        return redirect('peliculas:inicio')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next', '')
            
            if user.is_staff or user.is_superuser:
                if next_url and not next_url.startswith('/panel/'):
                    return redirect(next_url)
                messages.success(
                    request,
                    f'¡Bienvenido al panel, {user.first_name or user.username}!'
                )
                return redirect('panel:inicio')
            else:
                messages.success(
                    request,
                    f'¡Bienvenido de nuevo, {user.first_name or user.username}!'
                )
                if next_url:
                    return redirect(next_url)
                return redirect('peliculas:inicio')
 
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
 
    # MODIFICACION DE GEMINI
    peliculas_poster = Pelicula.objects.filter(poster__isnull=False)[:6]
    contexto = {
        'peliculas_poster': peliculas_poster
    }
    return render(request, 'usuarios/login.html', contexto)
    # FIN MODIFICACION DE GEMINI

############################################################################

@login_required
def logout_view(request):
    era_staff = request.user.is_staff or request.user.is_superuser
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    if era_staff:
        return redirect('usuarios:login')
    return redirect('peliculas:inicio')

############################################################################

@login_required
def perfil(request):
    total_reservas = request.user.reservas.count()
    reservas_activas = request.user.reservas.filter(estado='confirmada').count()
    reservas_pendientes = request.user.reservas.filter(estado='pendiente').count()
    # MODIFICACION DE GEMINI
    form = EditarPerfilForm(instance=request.user.perfil)
    password_form = PasswordChangeForm(request.user)
    contexto = {
        'usuario': request.user,
        'total_reservas': total_reservas,
        'reservas_activas': reservas_activas,
        'reservas_pendientes': reservas_pendientes,
        'form': form,
        'password_form': password_form,
    }
    # FIN MODIFICACION DE GEMINI
    return render(request, 'usuarios/perfil.html', contexto)

############################################################################

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        form = EditarPerfilForm(request.POST, instance=request.user.perfil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')
            return redirect('usuarios:perfil')
    else:
        form = EditarPerfilForm(instance=request.user.perfil)
    
    contexto = {
        'form': form
    }
    return render(request, 'usuarios/editar_perfil.html', contexto)

############################################################################

@login_required
def cambiar_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Mantiene la sesión activa
            messages.success(request, 'Tu contraseña ha sido cambiada exitosamente.')
            return redirect('usuarios:perfil')
    else:
        form = PasswordChangeForm(request.user)
    
    contexto = {
        'form': form
    }
    return render(request, 'usuarios/cambiar_password.html', contexto)