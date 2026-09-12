# modificado (Paso 0 - split de panel/views.py): módulo extraído automáticamente,
# sin cambios de lógica, solo de ubicación. Ver panel/views/__init__.py.

from django.shortcuts import render
from ..decorators import staff_required


# ============================================================
# VERIFICADOR QR (ahora vive en el panel)
# ============================================================

@staff_required
def verificador_qr(request):
    contexto = {
        'seccion_activa': 'verificador',
    }
    return render(request, 'panel/verificador_qr.html', contexto)
