# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from django.contrib import messages
from django.shortcuts import render, redirect
from ..decorators import staff_required
from ..models import ConfiguracionGeneral
from ..forms import (
    ConfiguracionGeneralForm,
)


# ============================================================
# CONFIGURACIÓN GENERAL (precio base de la entrada, etc)
# ============================================================
@staff_required
def configuracion_general(request):
    """
    Pantalla del panel para editar la configuración general del sistema
    (por ahora: precio base de la entrada). Es una fila única en la base
    (ConfiguracionGeneral.obtener()), así que cambiar el número acá no
    requiere ningún makemigrations/migrate.
    """
    config = ConfiguracionGeneral.obtener()

    if request.method == 'POST':
        form = ConfiguracionGeneralForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración general actualizada.')  # modificado - se quitó el emoji
            return redirect('panel:configuracion_general')
    else:
        form = ConfiguracionGeneralForm(instance=config)

    return render(request, 'panel/config_general/general.html', {
        'form': form,
        'config': config,
        'seccion_activa': 'configuracion',
    })
