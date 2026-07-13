------------------------------------------------------------------------------------------------------
##################################################################################################
#Los tres features nuevos FALTAN (confirmado: ninguno de los tres tiene código todavía)
1- Paginación en lista de películas
2- Rating/puntuación por usuarios
3- Historial de películas vistas
    (El rating y el historial necesitan modelos nuevos pero son simples.)
#Pulido general
Separar CSS y JS de los templates (esto lleva tiempo pero queda muy prolijo) — pendiente, se deja para el final.

~~Revisar bugs conocidos (el reload cada 10s en mis_reservas, entre otros)~~ 
RESUELTO — era cada 30s (no 10s), hacía location.reload() completo. Se reemplazó por una cuenta regresiva en JS por cada reserva pendiente (usa tiempo_restante_pago() que ya existía en el modelo), sin recargar la página. Solo recarga una vez, cuando una reserva puntual llega a 0, para reflejar la expiración real.

Consistencia visual entre templates — pendiente, se deja para el final.
##################################################################################################
------------------------------------------------------------------------------------------------------

### ------------------------------------------------------------------------------------------------------
1. Estadísticas de promociones en dashboard (pendiente, no evaluado en esta sesión)
Cupones: cuántos usados hoy/semana/mes, cuáles son los más populares
Combos: cuántos vendidos, ingresos generados
Promociones 2x1: cuántas reservas se beneficiaron
Se puede mostrar en la vista staff que ya tenés, con tarjetas de resumen arriba.

2. Precio diferenciado por tipo de sala — PENDIENTE, EN DEFINICIÓN. Actualmente el
precio lo maneja Funcion.precio manualmente (confirmado: no hay multiplicador en Sala).
Propuesta sobre la mesa: agregar un multiplicador a Sala (2D = x1, 3D = x1.20, Premium
= x1.50), aplicado automáticamente al crear una función, con el precio final
sobreescribible a mano por el admin. A validar el diseño antes de programarlo.
### ------------------------------------------------------------------------------------------------------

### ------------------------------------------------------------------------------------------------------
3. Bloquear asientos específicos. 
HECHO EN SU BASE — el modelo AsientoBloqueado ya existe (sala + asiento_codigo + motivo + función opcional), con su propio panel (`panel/salas/asientos`). Se arregló además un bug real de validación (`AsientoBloqueado.clean()` no reconocía los códigos de asiento por un cambio de formato en `layout_asientos()`). Lo que queda pendiente es lo de MEJORAS PRINCIPALES de abajo (selector visual, motivo VIP con recargo, bloqueo masivo, reserva manual).

Sigue usando el modelo de secciones (Opción A), no se migró a layout JSON.
### ------------------------------------------------------------------------------------------------------

# MEJORAS PRINCIPALES (todas pendientes, sobre la base ya existente de AsientoBloqueado)
1.Selector visual tipo "pintar asientos" admin ve el mapa, hace clic en asientos para asignarles un motivo (toggle de color), en vez de un formulario con checkboxes por asiento.

2.Bloqueo permanente vs. por función (funcion opcional). admin bloquea "asiento siempre" (butaca rota) o "solo para esta función" (evento privado, cortesía prensa).
[Nota: el bug de validación que rompía esto ("A1 no existe en la sala") ya se arregló.]

3.Precio diferenciado para asientos VIP si el motivo es vip, que sume un recargo fijo o porcentual al precio de esa función. Le da utilidad real al motivo VIP más allá de ser solo un color. lo quiero

4.Bloqueo masivo por sección/fila — en vez de clickear asiento por asiento, un botón "bloquear toda la fila A" o "bloquear sección completa". lo quiero

5.Reservar asientos "a mano" para casos especiales — cortesías, prensa, grupos que pagaron por teléfono — usando el motivo reservado sin pasar por el flujo normal de Reserva. lo quiero

# MEJORAS ESPECIFICAS (todas pendientes, no evaluadas en el código todavía)

-En panel/funciones cambiar a buscador con palabras tipo netflix. los demás filtros están perfectos
-En los tipos salas que el nombre de la sala este automatizado y que el nombre este default según que sala eligio y sea editabe según quiera elusuario admin
-Poner un precio general y no según cada pelicula o que sea default y editable según que se le antoje al usuario
-Mostrar en panel/funciones el tiempo en el que la pelicula siguiente se va a poder presentar en la misma sala por el ya que el solapamiento no sabemos exactamente a que hora podemos poner la siguiente pelicula solo sabemos que debemos dejar un margen especifico

# ORDEN ACORDADO PARA ESTA TANDA (11/07)
1. Precio por tipo de sala (definir diseño primero)
2. Fix reload mis_reservas — HECHO (ver arriba)
3. Carrito de compra
4. Buscador tipo Netflix en funciones + mejoras de AsientoBloqueado
Todo lo de diseño/CSS-JS puro, al final.
