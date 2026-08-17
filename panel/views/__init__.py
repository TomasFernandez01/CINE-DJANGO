# modificado (Paso 0 - split de panel/views.py en paquete panel/views/):
# reexporta todas las vistas para que panel/urls.py siga funcionando
# exactamente igual (sigue haciendo 'from . import views' y llamando
# views.nombre_funcion sin ningún cambio).

from .dashboard import (
    dashboard_grafico_combos,
    dashboard_grafico_ventas,
    dashboard_kpis,
    inicio,
)  # modificado: se suman los 3 endpoints AJAX nuevos del dashboard
from .peliculas import (
    peliculas_buscar_tmdb,
    peliculas_crear,
    peliculas_detalle,
    peliculas_editar,
    peliculas_eliminar,
    peliculas_importar_tmdb,
    peliculas_lista,
)
from .salas import (
    salas_asientos,
    salas_asientos_bloquear,
    salas_asientos_desbloquear,
    salas_categoria_asignar,
    salas_categoria_quitar,
    salas_crear,
    salas_editar,
    salas_eliminar,
    salas_lista,
)
from .funciones import (
    funciones_crear,
    funciones_detalle,
    funciones_editar,
    funciones_eliminar,
    funciones_lista,
    funciones_margen_tiempo,
)
from .reservas import (
    reservas_detalle,
    reservas_editar,
    reservas_lista,
)
from .pagos import (
    pagos_estadisticas,
    pagos_lista,
)
from .usuarios import (
    usuarios_crear,
    usuarios_detalle,
    usuarios_editar,
    usuarios_lista,
)
from .verificador_qr import verificador_qr
from .promociones import (
    combos_crear,
    combos_editar,
    combos_eliminar,
    combos_lista,
    cupones_crear,
    cupones_editar,
    cupones_eliminar,
    cupones_estadisticas,
    cupones_lista,
    cupones_usados_lista,
    promodia_crear,
    promodia_editar,
    promodia_eliminar,
    promodia_lista,
)
from .config_general import configuracion_general
# nuevo (Sedes - Fase 3)
from .sedes import (
    cambiar_sede_panel,
    sedes_crear,
    sedes_editar,
    sedes_eliminar,
    sedes_lista,
)
