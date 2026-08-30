# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from ..decorators import staff_required, get_sede_staff, superuser_required  # modificado (T14)
from ..models import ConfiguracionGeneral
from ..forms import (
    ConfiguracionGeneralForm,
)


# ============================================================
# CONFIGURACIÓN GENERAL (precio base de la entrada, etc)
# ============================================================
# modificado (T9 - Config General por sede): antes esta vista editaba
# siempre la única fila global (ConfiguracionGeneral.obtener()). Ahora:
# - SuperUser: puede elegir "Global" o cualquier sede con un selector
#   (?sede_id=<id> por GET) y edita la fila de lo que haya elegido.
# - Staff restringido a una sede (get_sede_staff devuelve algo distinto de
#   None): no hay selector, siempre edita la fila de su propia sede — sin
#   posibilidad de tocar la config de otra sede ni la global.
# Si la sede elegida/fija todavía no tiene su propia fila, se le muestran
# los valores heredados de la global como punto de partida (sin guardar
# nada todavía); el primer "Guardar" crea la fila propia de esa sede.
#
# modificado (T14 - reorg Administración): se decidió que Configuración
# General pasa a ser 100% SuperUser (toca precios, tiempos de reserva y
# credenciales de email — no tiene sentido dejarlo abierto a cada Staff de
# sede). @staff_required -> @superuser_required. La rama de "Staff
# restringido a su sede" de acá abajo queda como código muerto: no se
# borró porque no molesta y si el día de mañana se decide devolverle el
# acceso a Staff, ya está la lógica lista — pero hoy `get_sede_staff` va a
# devolver siempre None acá porque solo entra un SuperUser.
@superuser_required
def configuracion_general(request):
    """
    Pantalla del panel para editar la configuración general del sistema.
    Puede ser la configuración global de la cadena, o la de una sede en
    particular (ver ConfiguracionGeneral.obtener() en panel/models.py).
    Cambiar los valores acá no requiere ningún makemigrations/migrate
    adicional — la única migración de esta tanda es la que agrega el
    campo `sede`, que el dueño del proyecto corre antes de usar esto.
    """
    from sedes.models import Sede

    sede_fija = get_sede_staff(request.user)  # None si es SuperUser

    if sede_fija is not None:
        # Staff de una sede puntual: no elige, siempre es la suya.
        sede_seleccionada = sede_fija
    else:
        # SuperUser: "Global" (sin parámetro / vacío) o la sede que elija.
        sede_id = request.POST.get('sede_id') or request.GET.get('sede_id')
        sede_seleccionada = Sede.objects.filter(id=sede_id).first() if sede_id else None

    config_global = ConfiguracionGeneral.obtener()  # sede=None, de siempre

    creando_desde_global = False
    if sede_seleccionada is None:
        config = config_global
    else:
        config_propia = ConfiguracionGeneral.objects.filter(sede=sede_seleccionada).first()
        if config_propia is not None:
            config = config_propia
        else:
            # Todavía no existe fila propia para esta sede: se arma una
            # instancia en memoria (sin guardar) clonando los valores de
            # la global, como punto de partida para editar y crear.
            creando_desde_global = True
            config = ConfiguracionGeneral(sede=sede_seleccionada)
            for campo in ConfiguracionGeneralForm.Meta.fields:
                setattr(config, campo, getattr(config_global, campo))

    if request.method == 'POST':
        form = ConfiguracionGeneralForm(request.POST, instance=config)
        if form.is_valid():
            instancia = form.save(commit=False)
            instancia.sede = sede_seleccionada  # 'sede' no está en el form, se fija acá
            instancia.save()
            if sede_seleccionada is not None:
                messages.success(request, f'Configuración de {sede_seleccionada.nombre} actualizada.')
            else:
                messages.success(request, 'Configuración general (global) actualizada.')
            url = reverse('panel:configuracion_general')
            if sede_seleccionada is not None:
                url += f'?sede_id={sede_seleccionada.id}'
            return redirect(url)
    else:
        form = ConfiguracionGeneralForm(instance=config)

    return render(request, 'panel/config_general/general.html', {
        'form': form,
        'config': config,
        'seccion_activa': 'configuracion',
        'sede_fija': sede_fija,
        'sede_seleccionada': sede_seleccionada,
        'sedes_disponibles': Sede.objects.filter(activa=True) if sede_fija is None else None,
        'creando_desde_global': creando_desde_global,
    })

