// modificado: extraído del <script> inline de crear_reserva.html.
// Los valores que antes venían directo del template ({{ funcion.precio_final }},
// {{ asientos_disponibles }}) ahora se leen desde data-attributes en el
// contenedor #reservaCrearData (ver crear_reserva.html).
(function () {
    const datos = document.getElementById('reservaCrearData');
    if (!datos) return;

    const precioUnitario = parseFloat(datos.dataset.precioUnitario);
    const asientosDisponibles = parseInt(datos.dataset.asientosDisponibles, 10);

    const cantidadInput = document.getElementById('cantidad_entradas');
    const totalSpan = document.getElementById('total');

    cantidadInput.addEventListener('input', function () {
        let cantidad = parseInt(this.value) || 1;

        // Validar límites
        if (cantidad < 1) cantidad = 1;
        if (cantidad > 5) cantidad = 5;
        if (cantidad > asientosDisponibles) cantidad = asientosDisponibles;

        this.value = cantidad;
        const total = precioUnitario * cantidad;
        totalSpan.textContent = total.toFixed(2);
    });

    // Actualizar máximo según disponibilidad
    if (asientosDisponibles < 10) {
        cantidadInput.max = asientosDisponibles;
    }
})();
