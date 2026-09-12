from .models import Sede


def sede_actual(request):
    """
    Expone la sede elegida por el usuario (guardada en sesión) y la lista
    de sedes activas a TODOS los templates, para poder mostrar el
    selector "Elegí tu cine" en la navbar (base.html) sin tener que
    pasarlo manualmente en cada vista.

    request.session['sede_id'] es la fuente de verdad. Si no hay nada en
    sesión (usuario nuevo, o nunca eligió), sede_actual queda en None —
    las vistas que filtran por sede deben tratar ese caso como "sin
    filtrar" (mostrar todo), no como error.
    """
    sede = None
    sede_id = request.session.get('sede_id')
    if sede_id:
        sede = Sede.objects.filter(id=sede_id, activa=True).first()
        # si la sede guardada en sesión fue desactivada o borrada,
        # se limpia sola de la sesión para no quedar apuntando a nada
        if sede is None:
            request.session.pop('sede_id', None)

    return {
        'sede_actual': sede,
        'sedes_disponibles': Sede.objects.filter(activa=True),
    }
