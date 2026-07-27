// modificado (combos múltiples): reemplaza la lógica de radio-buttons
// (un solo combo posible) por un carrito real — cada ítem tiene su propio
// stepper independiente, se puede elegir cualquier combinación con
// cantidad propia por ítem. Extraído del <script> inline original.
(function () {
    const datos = document.getElementById('elegirComboData');
    if (!datos) return;

    const TOTAL_ENTRADAS = parseFloat(datos.dataset.totalEntradas);
    // ITEMS: [{id, nombre, precio}, ...] — todos los ítems activos, para
    // poder armar el resumen sin tener que ir a buscar cada dato al DOM.
    const ITEMS = JSON.parse(document.getElementById('items-data').textContent);
    const ITEMS_POR_ID = {};
    ITEMS.forEach(function (i) { ITEMS_POR_ID[i.id] = i; });

    const inputItemsJson    = document.getElementById('inputItemsJson');
    const resumenItemsLista = document.getElementById('resumenItemsLista');
    const resumenItemsTotal = document.getElementById('resumenItemsTotal');
    const resumenTotalEl    = document.getElementById('resumenTotal');
    const MAX_POR_ITEM      = 10;

    // cantidades[id] = cantidad elegida de ese ítem (0 = no elegido)
    const cantidades = {};

    function precioTotalItems() {
        let total = 0;
        Object.keys(cantidades).forEach(function (id) {
            const cant = cantidades[id];
            if (cant > 0 && ITEMS_POR_ID[id]) {
                total += ITEMS_POR_ID[id].precio * cant;
            }
        });
        return total;
    }

    function actualizarResumen() {
        const idsElegidos = Object.keys(cantidades).filter(function (id) { return cantidades[id] > 0; });

        if (idsElegidos.length === 0) {
            resumenItemsLista.innerHTML = '<div class="pago-ec-resumen-vacio">Ningún ítem elegido</div>';
        } else {
            resumenItemsLista.innerHTML = idsElegidos.map(function (id) {
                const item = ITEMS_POR_ID[id];
                const cant = cantidades[id];
                const subtotal = (item.precio * cant).toFixed(2);
                const nombre = cant > 1 ? cant + 'x ' + item.nombre : item.nombre;
                return '<div class="pago-ec-resumen-item-fila"><span>' + nombre + '</span><span>+$' + subtotal + '</span></div>';
            }).join('');
        }

        const totalItems = precioTotalItems();
        resumenItemsTotal.textContent = '$' + totalItems.toFixed(2);
        resumenTotalEl.textContent = '$' + (TOTAL_ENTRADAS + totalItems).toFixed(2);

        // input oculto que se manda al servidor: [{id, cantidad}, ...]
        const payload = idsElegidos.map(function (id) {
            return { id: parseInt(id, 10), cantidad: cantidades[id] };
        });
        inputItemsJson.value = JSON.stringify(payload);
    }

    document.querySelectorAll('.pago-ec-item-card').forEach(function (card) {
        const id = card.dataset.itemId;
        cantidades[id] = 0;

        const btnMenos    = card.querySelector('.pago-ec-item-btn--menos');
        const btnMas      = card.querySelector('.pago-ec-item-btn--mas');
        const spanCantidad = card.querySelector('.pago-ec-item-cantidad');

        function refrescarCard() {
            spanCantidad.textContent = cantidades[id];
            card.classList.toggle('pago-ec-item-card--seleccionado', cantidades[id] > 0);
            btnMenos.disabled = cantidades[id] <= 0;
            btnMas.disabled = cantidades[id] >= MAX_POR_ITEM;
        }

        btnMenos.addEventListener('click', function () {
            cantidades[id] = Math.max(0, cantidades[id] - 1);
            refrescarCard();
            actualizarResumen();
        });
        btnMas.addEventListener('click', function () {
            cantidades[id] = Math.min(MAX_POR_ITEM, cantidades[id] + 1);
            refrescarCard();
            actualizarResumen();
        });

        refrescarCard();
    });

    actualizarResumen();
})();
