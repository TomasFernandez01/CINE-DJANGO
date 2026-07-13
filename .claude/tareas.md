---------------------------------------------------------------------------------------------------------------------------------------------
# TERMINADO =
- Fix del reload en mis_reservas — es lógica de frontend (JS), no diseño visual, así que entra en "resolver primero" aunque toque un template.

# PROCESO =
Precio por tipo de sala — pediste que valide con vos el diseño (multiplicador vs. override manual), así que conviene definirlo temprano porque puede afectar a Funcion y a los cálculos de pagos.

---------------------------------------------------------------------------------------------------------------------------------------------
### POR HACER :

# Rating de usuarios + Historial de vistas — son los dos modelos nuevos "simples" que el roadmap ya marcaba como fáciles. Arrancar por acá te da una victoria rápida y no depende de nada más.

# Paginación de películas — cambio acotado, mejora rendimiento real si tienen muchas películas cargadas.

# Carrito de compra — es el pendiente más grande de FINALIZANDO.md, y probablemente el que más impacto tiene. Yo lo pondría después de los anteriores porque es una feature nueva de punta a punta (modelo, vistas, lógica de sesión/stock), no un fix.

# Buscador tipo Netflix en funciones + AsientoBloqueado avanzado (pintar asientos, VIP, etc.) — dejarlos para el final de esta tanda de lógica, ya que son mejoras sobre features que ya andan, no bugs ni faltantes críticos.

# Al final de todo: separación de CSS/JS de los templates y consistencia visual, como pediste.
---------------------------------------------------------------------------------------------------------------------------------------------