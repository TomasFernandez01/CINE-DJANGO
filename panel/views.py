from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.http import JsonResponse                    # mapa-salas
from django.views.decorators.http import require_POST   # mapa-salas
from django.core.exceptions import ValidationError      # mapa-salas
from datetime import timedelta
from .decorators import staff_required, superuser_required
#### APPS
from peliculas.models import Pelicula
from salas.models import Sala, Funcion, AsientoBloqueado # mapa-salas
from reservas.models import Reserva
from pagos.models import Pago
from promociones.models import Cupon, PromocionDia, Combo, CuponUsado
from django.contrib.auth.models import User
# ============================================================
                                                                # V2
from .forms import (
    PeliculaForm, SalaForm, FuncionForm,
    CrearUsuarioForm, EditarUsuarioForm, ReservaForm,
    ComboForm, CuponForm, PromocionDiaForm,
    SeccionSalaFormSet,
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
            #---------------------------------------------------------------------------------
            # Si el formulario venía precargado desde TMDB (peliculas_importar_tmdb) y el usuario no subió un poster propio, bajamos ahora el poster original de TMDB. Recién acá se toca el disco/la base por eso.
            poster_url_tmdb = request.POST.get('poster_url_tmdb', '').strip()
            if poster_url_tmdb and not pelicula.poster:
                try:
                    resp = requests.get(poster_url_tmdb, timeout=10)
                    resp.raise_for_status()
                    nombre = f"{pelicula.titulo.lower().replace(' ', '_')[:40]}.jpg"
                    pelicula.poster.save(nombre, ContentFile(resp.content), save=True)
                except Exception:
                    pass  # se crea igual sin poster, no es un error bloqueante
            #---------------------------------------------------------------------------------
            messages.success(request, f'✅ Película "{pelicula.titulo}" creada exitosamente.')
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:peliculas_crear')
            return redirect('panel:peliculas_detalle', pelicula_id=pelicula.id)
    else:
        form = PeliculaForm()

    return render(request, 'panel/peliculas/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Película',
        'accion': 'crear',
        'seccion_activa': 'peliculas',
        # Si Validacion falla y formulario lo rellena TMDB (trae el campo oculto poster_url_tmdb en el POST), lo re-pasamos al contexto para no perder la preview del poster al re-renderizar.
        'poster_url_tmdb': request.POST.get('poster_url_tmdb', '') if request.method == 'POST' else '',
    })
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
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:peliculas_crear')
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
@require_POST
def peliculas_eliminar(request):
    """
    Borrado múltiple de películas, en dos pasos (mismo patrón que salas_eliminar):
      1. Sin 'confirmado': vista previa con cuántas funciones, reservas y pagos
         se van a borrar en cascada (Pelicula -> Funcion -> Reserva -> Pago).
      2. Con 'confirmado=1': borra de verdad.
    """
    ids = request.POST.getlist('seleccionadas')
    if not ids:
        messages.error(request, 'No seleccionaste ninguna película.')
        return redirect('panel:peliculas_lista')

    peliculas_qs = Pelicula.objects.filter(id__in=ids)
    if not peliculas_qs.exists():
        messages.error(request, 'Las películas seleccionadas ya no existen.')
        return redirect('panel:peliculas_lista')

    if request.POST.get('confirmado') == '1':
        titulos = list(peliculas_qs.values_list('titulo', flat=True))
        peliculas_qs.delete()  # cascada: borra también sus funciones, reservas y pagos
        messages.success(request, f'🗑️ Película(s) eliminada(s): {", ".join(titulos)}.')
        return redirect('panel:peliculas_lista')

    # Paso 1: vista previa de lo que se va a borrar en cascada
    resumen = []
    for pelicula in peliculas_qs:
        total_funciones = pelicula.funciones.count()
        total_reservas = Reserva.objects.filter(funcion__pelicula=pelicula).count()
        total_pagos = Pago.objects.filter(reserva__funcion__pelicula=pelicula).count()
        resumen.append({
            'pelicula': pelicula,
            'total_funciones': total_funciones,
            'total_reservas': total_reservas,
            'total_pagos': total_pagos,
        })

    return render(request, 'panel/peliculas/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
        'seccion_activa': 'peliculas',
    })
# ============================================================
# PELÍCULAS — T M D B
# ============================================================

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
    """
    Importa una película desde TMDB y redirige al formulario de edición. Precarga datos en el formulario (accion='crear'), SIN guardar en BD. El poster no se puede precargar en un <input type="file">, así que se muestra como preview y se pasa la URL original en un campo oculto: si el usuario no sube un poster propio, recién al guardar (en peliculas_crear) se descarga esa imagen.
    """
    if not TMDB_DISPONIBLE:
        messages.error(request, 'TMDB no está configurado.')
        return redirect('panel:peliculas_buscar_tmdb')

    response = importar_pelicula_tmdb(tmdb_id)
    if not response['success']:
        messages.error(request, f'Error: {response.get("error")}')
        return redirect('panel:peliculas_buscar_tmdb')

    data = response['data']

    # Verificar duplicado.Si ya existe una película con ese título, no tiene sentido precargar. un formulario de creación: mandamos a editar la que ya está.
    existente = Pelicula.objects.filter(titulo__iexact=data['titulo']).first()
    if existente:
        messages.warning(request, f'"{data["titulo"]}" ya existe. Podés editarla.')
        return redirect('panel:peliculas_editar', pelicula_id=existente.id)
    
    form = PeliculaForm(initial={
        'titulo': data['titulo'][:50],
        'sinopsis': data.get('sinopsis', ''),
        'duracion': data.get('duracion'),
        'genero': data.get('genero'),
        'clasificacion': data.get('clasificacion', 'ATP'),
        'director': data.get('director', ''),
        'actores': data.get('actores', ''),
        'año': data.get('año'),
    })

    messages.info(request, f'Datos de "{data["titulo"]}" importados desde TMDB. Revisá y guardá para crearla.')

    return render(request, 'panel/peliculas/form.html', {
        'form': form,
        'titulo_pagina': 'Agregar Película (desde TMDB)',
        'accion': 'crear',
        'seccion_activa': 'peliculas',
        'poster_url_tmdb': data.get('poster_url', ''),
    })
    # Crear película , comentar el anterior si no sirve y volver a este
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
            # No confirmamos en DB todavía: necesitamos que el formset valide las secciones contra los filas/columnas YA actualizados (aunque sea solo en memoria), no contra los valores viejos.
            sala_temp = form.save(commit=False)
            formset = SeccionSalaFormSet(request.POST, instance=sala_temp)

            if formset.is_valid():
                sala_temp.save()
                formset.save()
                messages.success(request, f'✅ Sala "{sala_temp.nombre}" creada.')
                if request.POST.get('guardar_y_agregar_otro'):
                    return redirect('panel:salas_crear')
                return redirect('panel:salas_lista')
        else:
            formset = SeccionSalaFormSet(request.POST, instance=Sala())
    else:
        form = SalaForm()
        formset = SeccionSalaFormSet(instance=Sala())

    return render(request, 'panel/salas/form.html', {
        'form': form,
        'formset': formset,
        'titulo_pagina': 'Agregar Sala',
        'accion': 'crear',
        'seccion_activa': 'salas',
    })
    ##############
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
            sala_temp = form.save(commit=False)
            formset = SeccionSalaFormSet(request.POST, instance=sala_temp)

            if formset.is_valid():
                sala_temp.save()
                formset.save()
                messages.success(request, f'✅ Sala "{sala_temp.nombre}" actualizada.')
                if request.POST.get('guardar_y_agregar_otro'):
                    return redirect('panel:salas_crear')
                return redirect('panel:salas_lista')
        else:
            formset = SeccionSalaFormSet(request.POST, instance=sala)
    else:
        form = SalaForm(instance=sala)
        formset = SeccionSalaFormSet(instance=sala)

    return render(request, 'panel/salas/form.html', {
        'form': form,
        'formset': formset,
        'objeto': sala,
        'titulo_pagina': f'Editar sala: {sala.nombre}',
        'accion': 'editar',
        'seccion_activa': 'salas',
    })

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

@staff_required
@require_POST
def salas_eliminar(request):
    """
    Borrado múltiple de salas, en dos pasos:
      1. Sin 'confirmado': muestra una vista previa con cuántas funciones y
         reservas se van a borrar en cascada (Sala -> Funcion -> Reserva).
      2. Con 'confirmado=1': borra de verdad.
    """
    ids = request.POST.getlist('seleccionadas')
    if not ids:
        messages.error(request, 'No seleccionaste ninguna sala.')
        return redirect('panel:salas_lista')

    salas_qs = Sala.objects.filter(id__in=ids)
    if not salas_qs.exists():
        messages.error(request, 'Las salas seleccionadas ya no existen.')
        return redirect('panel:salas_lista')

    if request.POST.get('confirmado') == '1':
        nombres = list(salas_qs.values_list('nombre', flat=True))
        salas_qs.delete()  # cascada: borra también sus funciones y reservas
        messages.success(request, f'🗑️ Sala(s) eliminada(s): {", ".join(nombres)}.')
        return redirect('panel:salas_lista')

    # Paso 1: vista previa de lo que se va a borrar en cascada
    resumen = []
    for sala in salas_qs:
        total_funciones = sala.funciones.count()
        total_reservas = Reserva.objects.filter(funcion__sala=sala).count()
        resumen.append({
            'sala': sala,
            'total_funciones': total_funciones,
            'total_reservas': total_reservas,
        })

    return render(request, 'panel/salas/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
        'seccion_activa': 'salas',
    })


################ SALAS — MAPA VISUAL DE ASIENTOS BLOQUEADOS
@staff_required
def salas_asientos(request, sala_id):
    """
    Mapa visual de la sala para que el staff bloquee/desbloquee asientos
    con un clic. Tiene dos "modos":
      - Permanente (sin función): afecta a la sala para siempre.
      - Una función puntual: afecta solo a esa función (además de lo
        permanente, que siempre se hereda).
    """
    sala = get_object_or_404(Sala, id=sala_id)

    funcion_id = request.GET.get('funcion', '')
    funcion_seleccionada = None
    if funcion_id:
        funcion_seleccionada = get_object_or_404(Funcion, id=funcion_id, sala=sala)

    # Bloqueos aplicables al modo actual
    if funcion_seleccionada:
        bloqueos = sala.bloqueos_asientos.filter(
            Q(funcion__isnull=True) | Q(funcion=funcion_seleccionada)
        )
    else:
        bloqueos = sala.bloqueos_asientos.filter(funcion__isnull=True)

    bloqueos_por_codigo = {b.asiento_codigo: b for b in bloqueos}

    # Todos los bloqueos de la sala (para el listado inferior, sin importar el modo actual)
    todos_los_bloqueos = sala.bloqueos_asientos.select_related('funcion__pelicula').order_by('asiento_codigo')

    funciones_sala = sala.funciones.filter(
        fecha_hora__gte=timezone.now()
    ).select_related('pelicula').order_by('fecha_hora')[:30]

    # Si hay una función seleccionada, mostramos también qué asientos ya
    # están vendidos/reservados (informativo, no se pueden bloquear desde acá).
    asientos_ocupados_reserva = []
    if funcion_seleccionada:
        asientos_ocupados_reserva = funcion_seleccionada.asientos_ocupados()

    contexto = {
        'sala': sala,
        'layout': sala.layout_asientos(),
        'bloqueos_por_codigo': bloqueos_por_codigo,
        'todos_los_bloqueos': todos_los_bloqueos,
        'funcion_seleccionada': funcion_seleccionada,
        'funciones_sala': funciones_sala,
        'asientos_ocupados_reserva': asientos_ocupados_reserva,
        'motivo_choices': AsientoBloqueado.MOTIVO_CHOICES,
        'seccion_activa': 'salas',
    }
    return render(request, 'panel/salas/asientos.html', contexto)


@staff_required
@require_POST
def salas_asientos_bloquear(request, sala_id):
    """Endpoint AJAX: crea un bloqueo para un asiento."""
    sala = get_object_or_404(Sala, id=sala_id)

    asiento_codigo = request.POST.get('asiento_codigo', '').strip()
    motivo = request.POST.get('motivo', 'admin')
    nota = request.POST.get('nota', '').strip()
    funcion_id = request.POST.get('funcion_id') or None

    funcion = None
    if funcion_id:
        funcion = get_object_or_404(Funcion, id=funcion_id, sala=sala)

    bloqueo = AsientoBloqueado(
        sala=sala,
        asiento_codigo=asiento_codigo,
        motivo=motivo,
        nota=nota,
        funcion=funcion,
    )
    try:
        bloqueo.full_clean()
    except ValidationError as e:
        errores = e.message_dict if hasattr(e, 'message_dict') else {'__all__': e.messages}
        return JsonResponse({'success': False, 'errors': errores}, status=400)

    bloqueo.save(skip_validation=True)  # ya se validó arriba con full_clean()

    return JsonResponse({
        'success': True,
        'bloqueo_id': bloqueo.id,
        'asiento_codigo': bloqueo.asiento_codigo,
        'motivo': bloqueo.motivo,
        'motivo_display': bloqueo.get_motivo_display(),
        'nota': bloqueo.nota,
        'permanente': bloqueo.funcion_id is None,
    })


@staff_required
@require_POST
def salas_asientos_desbloquear(request, sala_id):
    """Endpoint AJAX: elimina un bloqueo existente."""
    sala = get_object_or_404(Sala, id=sala_id)
    bloqueo_id = request.POST.get('bloqueo_id')

    bloqueo = get_object_or_404(AsientoBloqueado, id=bloqueo_id, sala=sala)
    asiento_codigo = bloqueo.asiento_codigo
    bloqueo.delete()

    return JsonResponse({'success': True, 'asiento_codigo': asiento_codigo})

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
                if request.POST.get('guardar_y_agregar_otro'):
                    return redirect('panel:funciones_crear')
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
                if request.POST.get('guardar_y_agregar_otro'):
                    return redirect('panel:funciones_crear')
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
@staff_required
@require_POST
def funciones_eliminar(request):
    """
    Borrado múltiple de funciones, en dos pasos (mismo patrón que salas_eliminar):
      1. Sin 'confirmado': vista previa con cuántas reservas y pagos se van a
         borrar en cascada (Funcion -> Reserva -> Pago).
      2. Con 'confirmado=1': borra de verdad.
    """
    ids = request.POST.getlist('seleccionadas')
    if not ids:
        messages.error(request, 'No seleccionaste ninguna función.')
        return redirect('panel:funciones_lista')

    funciones_qs = Funcion.objects.filter(id__in=ids).select_related('pelicula', 'sala')
    if not funciones_qs.exists():
        messages.error(request, 'Las funciones seleccionadas ya no existen.')
        return redirect('panel:funciones_lista')

    if request.POST.get('confirmado') == '1':
        descripciones = [
            f'{f.pelicula.titulo} ({f.fecha_hora.strftime("%d/%m/%Y %H:%M")})'
            for f in funciones_qs
        ]
        funciones_qs.delete()  # cascada: borra también sus reservas y pagos
        messages.success(request, f'🗑️ Función(es) eliminada(s): {", ".join(descripciones)}.')
        return redirect('panel:funciones_lista')

    # Paso 1: vista previa de lo que se va a borrar en cascada
    resumen = []
    for funcion in funciones_qs:
        total_reservas = funcion.reservas.count()
        total_pagos = Pago.objects.filter(reserva__funcion=funcion).count()
        resumen.append({
            'funcion': funcion,
            'total_reservas': total_reservas,
            'total_pagos': total_pagos,
        })

    return render(request, 'panel/funciones/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
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
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:combos_crear')
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
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:combos_crear')
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

@staff_required
@require_POST
def combos_eliminar(request):
    """
    Borrado múltiple de combos, en dos pasos (mismo patrón que salas_eliminar).
    A diferencia de Sala/Pelicula/Funcion, Combo NO borra en cascada: los Pagos
    que lo usaron quedan con combo=null (Pago.combo es on_delete=SET_NULL).
    """
    ids = request.POST.getlist('seleccionadas')
    if not ids:
        messages.error(request, 'No seleccionaste ningún combo.')
        return redirect('panel:combos_lista')

    combos_qs = Combo.objects.filter(id__in=ids)
    if not combos_qs.exists():
        messages.error(request, 'Los combos seleccionados ya no existen.')
        return redirect('panel:combos_lista')

    if request.POST.get('confirmado') == '1':
        nombres = list(combos_qs.values_list('nombre', flat=True))
        combos_qs.delete()
        messages.success(request, f'🗑️ Combo(s) eliminado(s): {", ".join(nombres)}.')
        return redirect('panel:combos_lista')

    # Paso 1: vista previa (no hay cascada, solo informamos pagos que quedarían sin combo)
    resumen = []
    for combo in combos_qs:
        total_pagos = Pago.objects.filter(combo=combo).count()
        resumen.append({
            'combo': combo,
            'total_pagos': total_pagos,
        })

    return render(request, 'panel/promociones/combos/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
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
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:cupones_crear')
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
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:cupones_crear')
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

@staff_required
@require_POST
def cupones_eliminar(request):
    """
    Borrado múltiple de cupones, en dos pasos (mismo patrón que salas_eliminar).
    Cupon SÍ borra en cascada su historial de usos (CuponUsado.cupon es CASCADE),
    pero los Pagos que lo usaron quedan con cupon_usado=null (SET_NULL), no se borran.
    """
    ids = request.POST.getlist('seleccionadas')
    if not ids:
        messages.error(request, 'No seleccionaste ningún cupón.')
        return redirect('panel:cupones_lista')

    cupones_qs = Cupon.objects.filter(id__in=ids)
    if not cupones_qs.exists():
        messages.error(request, 'Los cupones seleccionados ya no existen.')
        return redirect('panel:cupones_lista')

    if request.POST.get('confirmado') == '1':
        codigos = list(cupones_qs.values_list('codigo', flat=True))
        cupones_qs.delete()  # cascada: borra también su historial de usos (CuponUsado)
        messages.success(request, f'🗑️ Cupón(es) eliminado(s): {", ".join(codigos)}.')
        return redirect('panel:cupones_lista')

    # Paso 1: vista previa de lo que se va a borrar en cascada
    resumen = []
    for cupon in cupones_qs:
        total_usos = cupon.usos.count()
        resumen.append({
            'cupon': cupon,
            'total_usos': total_usos,
        })

    return render(request, 'panel/promociones/cupones/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
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
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:promodia_crear')
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
            if request.POST.get('guardar_y_agregar_otro'):
                return redirect('panel:promodia_crear')
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

@staff_required
@require_POST
def promodia_eliminar(request):
    """
    Borrado múltiple de promociones por día, en dos pasos (mismo patrón que
    salas_eliminar). PromocionDia NO borra en cascada: los Pagos que la usaron
    quedan con promo_dia=null (Pago.promo_dia es on_delete=SET_NULL).
    """
    ids = request.POST.getlist('seleccionadas')
    if not ids:
        messages.error(request, 'No seleccionaste ninguna promoción.')
        return redirect('panel:promodia_lista')

    promos_qs = PromocionDia.objects.filter(id__in=ids)
    if not promos_qs.exists():
        messages.error(request, 'Las promociones seleccionadas ya no existen.')
        return redirect('panel:promodia_lista')

    if request.POST.get('confirmado') == '1':
        nombres = list(promos_qs.values_list('nombre', flat=True))
        promos_qs.delete()
        messages.success(request, f'🗑️ Promoción(es) eliminada(s): {", ".join(nombres)}.')
        return redirect('panel:promodia_lista')

    # Paso 1: vista previa (no hay cascada, solo informamos pagos que quedarían sin promo)
    resumen = []
    for promo in promos_qs:
        total_pagos = Pago.objects.filter(promo_dia=promo).count()
        resumen.append({
            'promo': promo,
            'total_pagos': total_pagos,
        })

    return render(request, 'panel/promociones/promodia/confirmar_eliminar.html', {
        'resumen': resumen,
        'ids': ids,
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

# ============================================================
#   STAFFV2 stadisticas de cupones
# ============================================================

@staff_required
def cupones_estadisticas(request):
    """Estadísticas de uso de cupones (único dato realmente trackeado hoy)."""
    ahora = timezone.now()
    hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    semana = hoy - timedelta(days=7)
    mes = hoy - timedelta(days=30)

    usos_hoy = CuponUsado.objects.filter(fecha_uso__gte=hoy)
    usos_semana = CuponUsado.objects.filter(fecha_uso__gte=semana)
    usos_mes = CuponUsado.objects.filter(fecha_uso__gte=mes)

    stats = {
        'usos_hoy': usos_hoy.count(),
        'usos_semana': usos_semana.count(),
        'usos_mes': usos_mes.count(),
        'usos_total': CuponUsado.objects.count(),
        'descuento_hoy': usos_hoy.aggregate(t=Sum('descuento_aplicado'))['t'] or 0,
        'descuento_semana': usos_semana.aggregate(t=Sum('descuento_aplicado'))['t'] or 0,
        'descuento_mes': usos_mes.aggregate(t=Sum('descuento_aplicado'))['t'] or 0,
        'descuento_total': CuponUsado.objects.aggregate(t=Sum('descuento_aplicado'))['t'] or 0,
    }

    # Ranking histórico de cupones más usados
    top_cupones = CuponUsado.objects.values(
        'cupon__codigo', 'cupon__descripcion'
    ).annotate(
        veces_usado=Count('id'),
        descuento_generado=Sum('descuento_aplicado')
    ).order_by('-veces_usado')[:10]

    # Cupones activos que no se usaron en los últimos 30 días (candidatos a revisar)
    cupones_activos_sin_uso = Cupon.objects.filter(
        activo=True
    ).exclude(
        id__in=usos_mes.values_list('cupon_id', flat=True)
    ).order_by('-fecha_inicio')[:10]

    ultimos_usos = CuponUsado.objects.select_related(
        'cupon', 'usuario', 'reserva__funcion__pelicula'
    ).order_by('-fecha_uso')[:10]

    contexto = {
        'stats': stats,
        'top_cupones': top_cupones,
        'cupones_activos_sin_uso': cupones_activos_sin_uso,
        'ultimos_usos': ultimos_usos,
        'seccion_activa': 'cupones',
    }
    return render(request, 'panel/promociones/cupones/estadisticas.html', contexto)
