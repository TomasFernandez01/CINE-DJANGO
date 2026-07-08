from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta

from .decorators import staff_required, superuser_required

from peliculas.models import Pelicula
from salas.models import Sala, Funcion
from reservas.models import Reserva
from pagos.models import Pago
from promociones.models import Cupon, PromocionDia, Combo, CuponUsado
from django.contrib.auth.models import User
# ============================================================
                                                                # V2
from .forms import (
    PeliculaForm, SalaForm, FuncionForm,
    CrearUsuarioForm, EditarUsuarioForm, ReservaForm,
    ComboForm, CuponForm, PromocionDiaForm
)
from django.core.files.base import ContentFile
import requests

try:
    from utils.tmdb_api import buscar_pelicula_tmdb, importar_pelicula_tmdb
    TMDB_DISPONIBLE = True
except ImportError:
    TMDB_DISPONIBLE = False


# ============================================================
# PELÍCULAS — CRUD
# ============================================================

@staff_required
def peliculas_crear(request):
    if request.method == 'POST':
        form = PeliculaForm(request.POST, request.FILES)
        if form.is_valid():
            pelicula = form.save()
            messages.success(request, f'✅ Película "{pelicula.titulo}" creada exitosamente.')
            return redirect('panel:peliculas_detalle', pelicula_id=pelicula.id)
    else:
        form = PeliculaForm()

    return render(request, 'panel/peliculas/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Película',
        'accion': 'crear',
        'seccion_activa': 'peliculas',
    })


@staff_required
def peliculas_editar(request, pelicula_id):
    pelicula = get_object_or_404(Pelicula, id=pelicula_id)

    if request.method == 'POST':
        form = PeliculaForm(request.POST, request.FILES, instance=pelicula)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Película "{pelicula.titulo}" actualizada.')
            return redirect('panel:peliculas_detalle', pelicula_id=pelicula.id)
    else:
        form = PeliculaForm(instance=pelicula)

    return render(request, 'panel/peliculas/form.html', {
        'form': form,
        'objeto': pelicula,
        'titulo_pagina': f'Editar: {pelicula.titulo}',
        'accion': 'editar',
        'seccion_activa': 'peliculas',
    })


@staff_required
def peliculas_buscar_tmdb(request):
    """Búsqueda TMDB integrada en el panel."""
    resultados = []
    query = ''

    if request.method == 'GET' and 'q' in request.GET:
        query = request.GET.get('q', '').strip()
        if query and TMDB_DISPONIBLE:
            response = buscar_pelicula_tmdb(query)
            if response['success']:
                resultados = response['results']
                if not resultados:
                    messages.info(request, f'Sin resultados para "{query}"')
            else:
                messages.error(request, f'Error al buscar: {response.get("error")}')

    return render(request, 'panel/peliculas/buscar_tmdb.html', {
        'query': query,
        'resultados': resultados,
        'tmdb_disponible': TMDB_DISPONIBLE,
        'seccion_activa': 'peliculas',
    })


@staff_required
def peliculas_importar_tmdb(request, tmdb_id):
    """Importa una película desde TMDB y redirige al formulario de edición."""
    if not TMDB_DISPONIBLE:
        messages.error(request, 'TMDB no está configurado.')
        return redirect('panel:peliculas_buscar_tmdb')

    response = importar_pelicula_tmdb(tmdb_id)
    if not response['success']:
        messages.error(request, f'Error: {response.get("error")}')
        return redirect('panel:peliculas_buscar_tmdb')

    data = response['data']

    # Verificar duplicado
    existente = Pelicula.objects.filter(titulo__iexact=data['titulo']).first()
    if existente:
        messages.warning(request, f'"{data["titulo"]}" ya existe. Podés editarla.')
        return redirect('panel:peliculas_editar', pelicula_id=existente.id)

    # Crear película
    pelicula = Pelicula.objects.create(
        titulo=data['titulo'][:50],
        sinopsis=data.get('sinopsis', ''),
        duracion=data.get('duracion'),
        genero=data.get('genero'),
        clasificacion=data.get('clasificacion', 'ATP'),
        director=data.get('director', ''),
        actores=data.get('actores', ''),
        año=data.get('año'),
        en_cartelera=False,
    )

    # Descargar poster
    poster_url = data.get('poster_url')
    if poster_url:
        try:
            resp = requests.get(poster_url, timeout=10)
            resp.raise_for_status()
            nombre = f"{data['titulo'].lower().replace(' ', '_')[:40]}.jpg"
            pelicula.poster.save(nombre, ContentFile(resp.content), save=True)
            messages.success(request, f'✅ "{pelicula.titulo}" importada con poster.')
        except Exception:
            pelicula.save()
            messages.success(request, f'✅ "{pelicula.titulo}" importada (sin poster).')
    else:
        pelicula.save()
        messages.success(request, f'✅ "{pelicula.titulo}" importada.')

    return redirect('panel:peliculas_editar', pelicula_id=pelicula.id)


# ============================================================
# SALAS — CRUD
# ============================================================

@staff_required
def salas_crear(request):
    if request.method == 'POST':
        form = SalaForm(request.POST)
        if form.is_valid():
            sala = form.save()
            messages.success(request, f'✅ Sala "{sala.nombre}" creada.')
            return redirect('panel:salas_lista')
    else:
        form = SalaForm()

    return render(request, 'panel/salas/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Sala',
        'accion': 'crear',
        'seccion_activa': 'salas',
    })


@staff_required
def salas_editar(request, sala_id):
    sala = get_object_or_404(Sala, id=sala_id)

    if request.method == 'POST':
        form = SalaForm(request.POST, instance=sala)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Sala "{sala.nombre}" actualizada.')
            return redirect('panel:salas_lista')
    else:
        form = SalaForm(instance=sala)

    return render(request, 'panel/salas/form.html', {
        'form': form,
        'objeto': sala,
        'titulo_pagina': f'Editar sala: {sala.nombre}',
        'accion': 'editar',
        'seccion_activa': 'salas',
    })


# ============================================================
# FUNCIONES — CRUD
# ============================================================

@staff_required
def funciones_crear(request):
    if request.method == 'POST':
        form = FuncionForm(request.POST)
        if form.is_valid():
            try:
                funcion = form.save()
                messages.success(
                    request,
                    f'✅ Función de "{funcion.pelicula.titulo}" creada el '
                    f'{funcion.fecha_hora.strftime("%d/%m/%Y a las %H:%M")}.'
                )
                return redirect('panel:funciones_detalle', funcion_id=funcion.id)
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
    else:
        # Pre-seleccionar pelicula/sala si vienen como parámetros
        initial = {}
        if request.GET.get('pelicula'):
            initial['pelicula'] = request.GET.get('pelicula')
        if request.GET.get('sala'):
            initial['sala'] = request.GET.get('sala')
        form = FuncionForm(initial=initial)

    return render(request, 'panel/funciones/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Función',
        'accion': 'crear',
        'seccion_activa': 'funciones',
    })


@staff_required
def funciones_editar(request, funcion_id):
    funcion = get_object_or_404(Funcion, id=funcion_id)

    if request.method == 'POST':
        form = FuncionForm(request.POST, instance=funcion)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, '✅ Función actualizada.')
                return redirect('panel:funciones_detalle', funcion_id=funcion.id)
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
    else:
        form = FuncionForm(instance=funcion)

    return render(request, 'panel/funciones/form.html', {
        'form': form,
        'objeto': funcion,
        'titulo_pagina': f'Editar: {funcion.pelicula.titulo}',
        'accion': 'editar',
        'seccion_activa': 'funciones',
    })


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

# ============================================================
                                                                # V1
# HELPERS
# ============================================================

def _stats_generales():
    """Datos comunes que se muestran en varias vistas."""
    ahora = timezone.now()
    hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        'ahora': ahora,
        'hoy': hoy,
        'peliculas_cartelera': Pelicula.objects.filter(en_cartelera=True).count(),
        'funciones_hoy': Funcion.objects.filter(
            fecha_hora__gte=hoy,
            fecha_hora__lt=hoy + timedelta(days=1),
            disponible=True
        ).count(),
        'reservas_pendientes': Reserva.objects.filter(estado='pendiente').count(),
        'recaudado_hoy': Pago.objects.filter(
            estado='aprobado', fecha_pago__gte=hoy
        ).aggregate(t=Sum('monto'))['t'] or 0,
    }


# ============================================================
# DASHBOARD PRINCIPAL
# ============================================================

@staff_required
def inicio(request):
    ahora = timezone.now()
    hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    semana = hoy - timedelta(days=7)

    # Tarjetas de resumen
    stats = {
        'peliculas_cartelera': Pelicula.objects.filter(en_cartelera=True).count(),
        'peliculas_total': Pelicula.objects.count(),
        'funciones_hoy': Funcion.objects.filter(
            fecha_hora__gte=hoy,
            fecha_hora__lt=hoy + timedelta(days=1),
            disponible=True
        ).count(),
        'funciones_proximas': Funcion.objects.filter(
            fecha_hora__gte=ahora, disponible=True
        ).count(),
        'reservas_pendientes': Reserva.objects.filter(estado='pendiente').count(),
        'reservas_hoy': Reserva.objects.filter(fecha_reserva__gte=hoy).count(),
        'reservas_confirmadas_hoy': Reserva.objects.filter(
            estado='confirmada', fecha_reserva__gte=hoy
        ).count(),
        'recaudado_hoy': Pago.objects.filter(
            estado='aprobado', fecha_pago__gte=hoy
        ).aggregate(t=Sum('monto'))['t'] or 0,
        'recaudado_semana': Pago.objects.filter(
            estado='aprobado', fecha_pago__gte=semana
        ).aggregate(t=Sum('monto'))['t'] or 0,
        'qr_escaneados_hoy': Pago.objects.filter(
            qr_escaneado=True, fecha_escaneo__gte=hoy
        ).count(),
    }

    # Próximas funciones (hoy y mañana)
    proximas_funciones = Funcion.objects.filter(
        fecha_hora__gte=ahora,
        fecha_hora__lt=hoy + timedelta(days=2),
        disponible=True
    ).select_related('pelicula', 'sala').order_by('fecha_hora')[:8]

    # Últimas reservas
    ultimas_reservas = Reserva.objects.select_related(
        'usuario', 'funcion__pelicula'
    ).order_by('-fecha_reserva')[:8]

    # Últimos pagos
    ultimos_pagos = Pago.objects.filter(
        estado='aprobado'
    ).select_related(
        'reserva__usuario', 'reserva__funcion__pelicula'
    ).order_by('-fecha_pago')[:5]

    contexto = {
        'stats': stats,
        'proximas_funciones': proximas_funciones,
        'ultimas_reservas': ultimas_reservas,
        'ultimos_pagos': ultimos_pagos,
        'seccion_activa': 'inicio',
    }
    return render(request, 'panel/inicio.html', contexto)


# ============================================================
# PELÍCULAS
# ============================================================

@staff_required
def peliculas_lista(request):
    busqueda = request.GET.get('q', '')
    en_cartelera = request.GET.get('cartelera', '')

    peliculas = Pelicula.objects.all()
    if busqueda:
        peliculas = peliculas.filter(
            Q(titulo__icontains=busqueda) | Q(director__icontains=busqueda)
        )
    if en_cartelera == 'si':
        peliculas = peliculas.filter(en_cartelera=True)
    elif en_cartelera == 'no':
        peliculas = peliculas.filter(en_cartelera=False)

    peliculas = peliculas.order_by('-en_cartelera', 'titulo')

    contexto = {
        'peliculas': peliculas,
        'busqueda': busqueda,
        'en_cartelera': en_cartelera,
        'total': peliculas.count(),
        'seccion_activa': 'peliculas',
    }
    return render(request, 'panel/peliculas/lista.html', contexto)


@staff_required
def peliculas_detalle(request, pelicula_id):
    pelicula = get_object_or_404(Pelicula, id=pelicula_id)
    ahora = timezone.now()
    funciones = pelicula.funciones.filter(
        fecha_hora__gte=ahora
    ).select_related('sala').order_by('fecha_hora')

    contexto = {
        'pelicula': pelicula,
        'funciones': funciones,
        'seccion_activa': 'peliculas',
    }
    return render(request, 'panel/peliculas/detalle.html', contexto)


# ============================================================
# SALAS
# ============================================================

@staff_required
def salas_lista(request):
    salas = Sala.objects.all().order_by('nombre')
    ahora = timezone.now()

    salas_con_info = []
    for sala in salas:
        funciones_hoy = sala.funciones.filter(
            fecha_hora__gte=ahora.replace(hour=0, minute=0, second=0),
            fecha_hora__lt=ahora.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        ).count()
        salas_con_info.append({
            'sala': sala,
            'funciones_hoy': funciones_hoy,
        })

    contexto = {
        'salas_con_info': salas_con_info,
        'seccion_activa': 'salas',
    }
    return render(request, 'panel/salas/lista.html', contexto)


# ============================================================
# FUNCIONES
# ============================================================

@staff_required
def funciones_lista(request):
    ahora = timezone.now()
    filtro = request.GET.get('filtro', 'proximas')

    funciones = Funcion.objects.select_related('pelicula', 'sala').order_by('fecha_hora')

    if filtro == 'hoy':
        hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        funciones = funciones.filter(
            fecha_hora__gte=hoy,
            fecha_hora__lt=hoy + timedelta(days=1)
        )
    elif filtro == 'proximas':
        funciones = funciones.filter(fecha_hora__gte=ahora)
    elif filtro == 'pasadas':
        funciones = funciones.filter(fecha_hora__lt=ahora).order_by('-fecha_hora')
    elif filtro == 'todas':
        funciones = funciones.order_by('-fecha_hora')

    # NUEVO
    filtros_tabs = [
        ('hoy',      '📅 Hoy'),
        ('proximas', '⏭️ Próximas'),
        ('pasadas',  '⏮️ Pasadas'),
        ('todas',    '📋 Todas'),
        ]

    contexto = {
        'funciones': funciones[:50],
        'filtro': filtro,
        'total': funciones.count(),
        'filtros_tabs': filtros_tabs,
        'seccion_activa': 'funciones',
    }
    return render(request, 'panel/funciones/lista.html', contexto)


@staff_required
def funciones_detalle(request, funcion_id):
    funcion = get_object_or_404(Funcion, id=funcion_id)
    reservas = funcion.reservas.select_related(
        'usuario', 'pago'
    ).order_by('-fecha_reserva')

    entradas_vendidas = reservas.filter(
        estado='confirmada'
    ).aggregate(t=Sum('cantidad_entradas'))['t'] or 0

    recaudado = Pago.objects.filter(
        reserva__funcion=funcion,
        estado='aprobado'
    ).aggregate(t=Sum('monto'))['t'] or 0

    qr_escaneados = Pago.objects.filter(
        reserva__funcion=funcion,
        qr_escaneado=True
    ).count()

    contexto = {
        'funcion': funcion,
        'reservas': reservas,
        'entradas_vendidas': entradas_vendidas,
        'capacidad': funcion.sala.capacidad,
        'ocupacion_pct': int(entradas_vendidas / funcion.sala.capacidad * 100) if funcion.sala.capacidad else 0,
        'recaudado': recaudado,
        'qr_escaneados': qr_escaneados,
        'asientos_ocupados': funcion.asientos_ocupados(),
        'layout': funcion.sala.layout_asientos(),
        'seccion_activa': 'funciones',
    }
    return render(request, 'panel/funciones/detalle.html', contexto)


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
# PAGOS
# ============================================================

@staff_required
def pagos_lista(request):
    estado = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '')

    pagos = Pago.objects.select_related(
        'reserva__usuario',
        'reserva__funcion__pelicula'
    ).order_by('-fecha_pago')

    if estado:
        pagos = pagos.filter(estado=estado)
    if busqueda:
        pagos = pagos.filter(
            Q(numero_transaccion__icontains=busqueda) |
            Q(reserva__usuario__username__icontains=busqueda) |
            Q(reserva__codigo_reserva__icontains=busqueda)
        )

    total_filtrado = pagos.aggregate(t=Sum('monto'))['t'] or 0

    contexto = {
        'pagos': pagos[:60],
        'estado': estado,
        'busqueda': busqueda,
        'total_filtrado': total_filtrado,
        'total': pagos.count(),
        'seccion_activa': 'pagos',
    }
    return render(request, 'panel/pagos/lista.html', contexto)


@staff_required
def pagos_estadisticas(request):
    """Las estadísticas viven ahora en el panel."""
    ahora = timezone.now()
    hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    pagos_hoy = Pago.objects.filter(estado='aprobado', fecha_pago__gte=hoy)
    recaudado_hoy = pagos_hoy.aggregate(t=Sum('monto'))['t'] or 0
    entradas_hoy = pagos_hoy.aggregate(
        t=Sum('reserva__cantidad_entradas')
    )['t'] or 0

    total_recaudado = Pago.objects.filter(
        estado='aprobado'
    ).aggregate(t=Sum('monto'))['t'] or 0

    qr_escaneados_hoy = Pago.objects.filter(
        qr_escaneado=True, fecha_escaneo__gte=hoy
    ).count()
    qr_total = Pago.objects.filter(qr_escaneado=True).count()
    qr_pendientes = Pago.objects.filter(
        estado='aprobado',
        qr_escaneado=False,
        reserva__estado='confirmada',
        reserva__funcion__fecha_hora__gte=ahora
    ).count()

    funciones_hoy = Funcion.objects.filter(
        fecha_hora__gte=hoy,
        fecha_hora__lt=hoy + timedelta(days=1)
    ).select_related('pelicula', 'sala').order_by('fecha_hora')

    funciones_con_stats = []
    for f in funciones_hoy:
        vendidas = f.reservas.filter(
            estado='confirmada'
        ).aggregate(t=Sum('cantidad_entradas'))['t'] or 0
        cap = f.sala.capacidad
        funciones_con_stats.append({
            'funcion': f,
            'entradas_vendidas': vendidas,
            'capacidad': cap,
            'ocupacion_pct': int(vendidas / cap * 100) if cap else 0,
            'qr_escaneados': Pago.objects.filter(
                reserva__funcion=f, qr_escaneado=True
            ).count(),
        })

    ultimos_pagos = Pago.objects.filter(
        estado='aprobado'
    ).select_related(
        'reserva__usuario', 'reserva__funcion__pelicula'
    ).order_by('-fecha_pago')[:10]

    ultimos_escaneos = Pago.objects.filter(
        qr_escaneado=True
    ).select_related(
        'reserva__usuario',
        'reserva__funcion__pelicula',
        'reserva__funcion__sala'
    ).order_by('-fecha_escaneo')[:10]

    contexto = {
        'ahora': ahora,
        'recaudado_hoy': recaudado_hoy,
        'entradas_hoy': entradas_hoy,
        'total_recaudado': total_recaudado,
        'qr_escaneados_hoy': qr_escaneados_hoy,
        'qr_total': qr_total,
        'qr_pendientes': qr_pendientes,
        'funciones_con_stats': funciones_con_stats,
        'ultimos_pagos': ultimos_pagos,
        'ultimos_escaneos': ultimos_escaneos,
        'seccion_activa': 'pagos',
    }
    return render(request, 'panel/pagos/estadisticas.html', contexto)


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


# ============================================================
# VERIFICADOR QR (ahora vive en el panel)
# ============================================================

@staff_required
def verificador_qr(request):
    contexto = {
        'seccion_activa': 'verificador',
    }
    return render(request, 'panel/verificador_qr.html', contexto)

                                                                # V1
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

# ============================================================
# PROMOCIONES — COMBOS
# ============================================================

@staff_required
def combos_lista(request):
    combos = Combo.objects.all().order_by('precio')
    return render(request, 'panel/promociones/combos/lista.html', {
        'combos': combos,
        'seccion_activa': 'combos',
    })


@staff_required
def combos_crear(request):
    if request.method == 'POST':
        form = ComboForm(request.POST, request.FILES)
        if form.is_valid():
            combo = form.save()
            messages.success(request, f'✅ Combo "{combo.nombre}" creado.')
            return redirect('panel:combos_lista')
    else:
        form = ComboForm()

    return render(request, 'panel/promociones/combos/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Combo',
        'accion': 'crear',
        'seccion_activa': 'combos',
    })


@staff_required
def combos_editar(request, combo_id):
    combo = get_object_or_404(Combo, id=combo_id)

    if request.method == 'POST':
        form = ComboForm(request.POST, request.FILES, instance=combo)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Combo "{combo.nombre}" actualizado.')
            return redirect('panel:combos_lista')
    else:
        form = ComboForm(instance=combo)

    return render(request, 'panel/promociones/combos/form.html', {
        'form': form,
        'objeto': combo,
        'titulo_pagina': f'Editar: {combo.nombre}',
        'accion': 'editar',
        'seccion_activa': 'combos',
    })


# ============================================================
# PROMOCIONES — CUPONES
# ============================================================

@staff_required
def cupones_lista(request):
    busqueda = request.GET.get('q', '')
    estado = request.GET.get('estado', '')

    cupones = Cupon.objects.all().order_by('-fecha_inicio')
    if busqueda:
        cupones = cupones.filter(
            Q(codigo__icontains=busqueda) | Q(descripcion__icontains=busqueda)
        )
    if estado == 'activo':
        cupones = cupones.filter(activo=True)
    elif estado == 'inactivo':
        cupones = cupones.filter(activo=False)

    contexto = {
        'cupones': cupones,
        'busqueda': busqueda,
        'estado': estado,
        'total': cupones.count(),
        'seccion_activa': 'cupones',
    }
    return render(request, 'panel/promociones/cupones/lista.html', contexto)


@staff_required
def cupones_crear(request):
    if request.method == 'POST':
        form = CuponForm(request.POST)
        if form.is_valid():
            cupon = form.save()
            messages.success(request, f'✅ Cupón "{cupon.codigo}" creado.')
            return redirect('panel:cupones_lista')
    else:
        form = CuponForm()

    return render(request, 'panel/promociones/cupones/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Cupón',
        'accion': 'crear',
        'seccion_activa': 'cupones',
    })


@staff_required
def cupones_editar(request, cupon_id):
    cupon = get_object_or_404(Cupon, id=cupon_id)

    if request.method == 'POST':
        form = CuponForm(request.POST, instance=cupon)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Cupón "{cupon.codigo}" actualizado.')
            return redirect('panel:cupones_lista')
    else:
        form = CuponForm(instance=cupon)

    return render(request, 'panel/promociones/cupones/form.html', {
        'form': form,
        'objeto': cupon,
        'titulo_pagina': f'Editar: {cupon.codigo}',
        'accion': 'editar',
        'seccion_activa': 'cupones',
    })


# ============================================================
# PROMOCIONES — PROMOCIÓN POR DÍA
# ============================================================

@staff_required
def promodia_lista(request):
    promociones = PromocionDia.objects.all().order_by('dia_semana')
    return render(request, 'panel/promociones/promodia/lista.html', {
        'promociones': promociones,
        'seccion_activa': 'promodia',
    })


@staff_required
def promodia_crear(request):
    if request.method == 'POST':
        form = PromocionDiaForm(request.POST)
        if form.is_valid():
            promo = form.save()
            messages.success(request, f'✅ Promoción "{promo.nombre}" creada.')
            return redirect('panel:promodia_lista')
    else:
        form = PromocionDiaForm()

    return render(request, 'panel/promociones/promodia/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Promoción por Día',
        'accion': 'crear',
        'seccion_activa': 'promodia',
    })


@staff_required
def promodia_editar(request, promo_id):
    promo = get_object_or_404(PromocionDia, id=promo_id)

    if request.method == 'POST':
        form = PromocionDiaForm(request.POST, instance=promo)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Promoción "{promo.nombre}" actualizada.')
            return redirect('panel:promodia_lista')
    else:
        form = PromocionDiaForm(instance=promo)

    return render(request, 'panel/promociones/promodia/form.html', {
        'form': form,
        'objeto': promo,
        'titulo_pagina': f'Editar: {promo.nombre}',
        'accion': 'editar',
        'seccion_activa': 'promodia',
    })


# ============================================================
# CUPONES USADOS (solo lectura) — vive en Operaciones
# ============================================================

@staff_required
def cupones_usados_lista(request):
    busqueda = request.GET.get('q', '')

    historial = CuponUsado.objects.select_related(
        'cupon', 'usuario', 'reserva__funcion__pelicula'
    ).order_by('-fecha_uso')

    if busqueda:
        historial = historial.filter(
            Q(cupon__codigo__icontains=busqueda) |
            Q(usuario__username__icontains=busqueda)
        )

    contexto = {
        'historial': historial[:100],
        'busqueda': busqueda,
        'total': historial.count(),
        'seccion_activa': 'cupones_usados',
    }
    return render(request, 'panel/promociones/cupones_usados/lista.html', contexto)