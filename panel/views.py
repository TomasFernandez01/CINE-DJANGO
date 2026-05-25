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
from django.contrib.auth.models import User


# ============================================================
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