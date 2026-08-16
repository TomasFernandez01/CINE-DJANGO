# nuevo (Sedes - Fase 3): expone al sidebar/topbar del Panel (base_panel.html)
# si el staff está restringido a una sede fija, cuál es la sede activa
# (fija o elegida), y la lista de sedes para el selector. Solo hace las
# queries si el usuario es staff — no afecta al resto del sitio.

from sedes.models import Sede
from .decorators import get_sede_staff, get_sede_activa_panel


def sede_panel_context(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}
    return {
        'panel_sede_fija': get_sede_staff(request.user),
        'panel_sede_activa': get_sede_activa_panel(request),
        'panel_sedes_disponibles': Sede.objects.filter(activa=True),
    }
