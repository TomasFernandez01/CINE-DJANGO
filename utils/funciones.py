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
    ninguna funcion."""
    from salas.models import Sala  # import local para evitar import circular a nivel de modulo

    por_tipo = {}
    for funcion in funciones_iterable:
        por_tipo.setdefault(funcion.sala.tipo, []).append(funcion)

    grupos = []
    for valor_tipo, etiqueta_tipo in Sala.TIPO_CHOICES:
        if valor_tipo in por_tipo:
            grupos.append({
                'tipo': valor_tipo,
                'etiqueta': etiqueta_tipo,
                'funciones': por_tipo[valor_tipo],
            })
    return grupos
