"""
utils/funciones.py

Helper compartido para agrupar funciones por tipo de sala (2D/3D/2D Premium/
3D Premium), respetando el orden de Sala.TIPO_CHOICES. Antes esta logica
vivia duplicada adentro de peliculas.views.detalle_pelicula; ahora tambien
la usa salas.views.lista_funciones (tanda 3) para armar, por cada pelicula,
sus horarios agrupados por tipo de sala.
"""


def agrupar_por_tipo_sala(funciones_iterable):
    """Recibe un iterable de Funcion (ya filtradas) y devuelve una lista de
    dicts: [{'tipo': '2d', 'etiqueta': '2D', 'funciones': [...]}, ...]
    en el orden definido por Sala.TIPO_CHOICES, salteando los tipos sin
    ninguna funcion.

    nuevo (Sedes - tareasnuevas punto 2): si el conjunto mezcla funciones
    de MÁS DE UNA sede (típico cuando el cliente no eligió sede en el
    selector "Elegí tu cine"), se agrupa también por sede — si no, un
    mismo grupo "2D" mezclaría horarios de sedes distintas sin ninguna
    forma de distinguirlos. La etiqueta pasa a ser "2D — San Justo" en
    ese caso. Cuando hay una sola sede en juego (el caso normal, con
    sede elegida), la etiqueta queda igual que antes."""
    from salas.models import Sala  # import local para evitar import circular a nivel de modulo

    funciones_list = list(funciones_iterable)
    sedes_distintas = {f.sala.sede_id for f in funciones_list}
    mostrar_sede = len(sedes_distintas) > 1

    por_clave = {}
    orden_claves = []
    for funcion in funciones_list:
        clave = (funcion.sala.tipo, funcion.sala.sede_id if mostrar_sede else None)
        if clave not in por_clave:
            por_clave[clave] = []
            orden_claves.append(clave)
        por_clave[clave].append(funcion)

    orden_tipos = [valor for valor, _ in Sala.TIPO_CHOICES]
    orden_claves.sort(key=lambda c: orden_tipos.index(c[0]))
    etiquetas_tipo = dict(Sala.TIPO_CHOICES)

    grupos = []
    for tipo, sede_id in orden_claves:
        funciones_grupo = por_clave[(tipo, sede_id)]
        etiqueta = etiquetas_tipo[tipo]
        if mostrar_sede:
            etiqueta = f"{etiqueta} — {funciones_grupo[0].sala.sede.nombre}"
        grupos.append({
            'tipo': tipo,
            'etiqueta': etiqueta,
            'funciones': funciones_grupo,
        })
    return grupos
