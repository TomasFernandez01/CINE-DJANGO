// modificado: extraído del <script> inline de elegir_entrada.html.
// Los valores que antes venían directo del template ({{ funcion.precio_final }},
// {{ max_cantidad }}, el loop de promos_dia_activas) ahora se leen desde
// data-attributes y un json_script en el contenedor #elegirEntradaData
// (ver elegir_entrada.html), en vez de estar embebidos en el JS.
(function () {
    const datos = document.getElementById('elegirEntradaData');
    if (!datos) return;

    const PRECIO_UNITARIO = parseFloat(datos.dataset.precioUnitario);
    const MAX_CANTIDAD = parseInt(datos.dataset.maxCantidad, 10);
    const PROMOS = JSON.parse(document.getElementById('promos-dia-activas-data').textContent);

    let cantidad = 1;
    let tipoSeleccionado = 'general';  // 'general' | 'cupon' | 'promo_dia_<id>'

    const inputCantidad     = document.getElementById('inputCantidad');
    const cantidadVisible   = document.getElementById('cantidadVisible');
    const btnMenos          = document.getElementById('btnMenos');
    const btnMas            = document.getElementById('btnMas');
    const avisoCantidadPar  = document.getElementById('avisoCantidadPar');
    const cajaCantidad      = document.getElementById('cajaCantidadEntrada'); // modificado (punto 1b)
    const resumenEntradasEl = document.getElementById('resumenEntradasTexto');
    const resumenTotalEl    = document.getElementById('resumenTotal');
    const tarjetas          = document.querySelectorAll('.tarjeta-tipo-entrada');

    // modificado: helper nuevo — busca en PROMOS la que corresponde a la
    // tarjeta actualmente seleccionada (o null si no es una tarjeta de promo)
    function promoSeleccionada() {
        if (!tipoSeleccionado.startsWith('promo_dia_')) return null;
        const id = parseInt(tipoSeleccionado.replace('promo_dia_', ''), 10);
        return PROMOS.find(function (p) { return p.id === id; }) || null;
    }

    function pasoIncremento() {
        // modificado: si eligieron una promo 2x1, conviene moverse de a 2 en 2
        const promo = promoSeleccionada();
        return (promo && promo.tipo === '2x1') ? 2 : 1;
    }

    function calcularTotal() {
        let subtotal = PRECIO_UNITARIO * cantidad;
        let descuento = 0;
        const promo = promoSeleccionada();

        if (promo) {
            if (promo.tipo === '2x1') {
                const entradasGratis = Math.floor(cantidad / 2);
                descuento = (subtotal / cantidad) * entradasGratis;
            } else if (promo.tipo === 'descuento') {
                descuento = subtotal * (promo.porcentaje / 100);
            }
        }
        // El cupón se valida recién en el servidor (necesita consultar la base),
        // acá no se descuenta nada todavía — el total con cupón se confirma
        // después de enviar el formulario.

        return Math.max(0, subtotal - descuento);
    }

    function actualizarResumen() {
        cantidadVisible.textContent = cantidad;
        inputCantidad.value = cantidad;

        const promo = promoSeleccionada();
        let etiquetaTipo = 'entrada general';
        if (promo) etiquetaTipo = promo.nombre;
        if (tipoSeleccionado === 'cupon') etiquetaTipo = 'con cupón (a validar)';

        resumenEntradasEl.textContent = cantidad + ' · ' + etiquetaTipo;
        resumenTotalEl.textContent = '$' + calcularTotal().toFixed(2);

        const requierePar = promo && promo.tipo === '2x1';
        // modificado: se usa una clase modificadora en vez de tocar style.display directo
        avisoCantidadPar.classList.toggle('reserva-ee-aviso-par--visible', requierePar && cantidad % 2 !== 0);

        btnMenos.disabled = cantidad <= 1;
        btnMas.disabled = cantidad >= MAX_CANTIDAD;
    }

    btnMenos.addEventListener('click', function () {
        const paso = pasoIncremento();
        cantidad = Math.max(1, cantidad - paso);
        actualizarResumen();
    });

    btnMas.addEventListener('click', function () {
        const paso = pasoIncremento();
        cantidad = Math.min(MAX_CANTIDAD, cantidad + paso);
        actualizarResumen();
    });

    // modificado: la lógica de "seleccionar esta tarjeta" se saca a una
    // función aparte, en vez de vivir solo adentro del listener de click.
    // Antes, para seleccionar la tarjeta de cupón al enfocar el input de
    // texto, se llamaba a tarjeta.click() — pero como el <label> envuelve
    // DOS controles (el radio y el input de texto), el navegador interpreta
    // ese click() como "activar el primer control del label" (el radio),
    // y eso le robaba el foco al input apenas lo ganaba: no dejaba escribir
    // ni una letra. Ahora se llama directamente a esta función, sin pasar
    // por ningún click() simulado sobre el label.
    function seleccionarTarjeta(tarjeta) {
        tarjetas.forEach(function (t) { t.classList.remove('seleccionada'); });
        tarjeta.classList.add('seleccionada');
        const radio = tarjeta.querySelector('input[type="radio"]');
        radio.checked = true;
        tipoSeleccionado = tarjeta.dataset.valor;

        // modificado (punto 1b de revisión): recién ahora se revela la caja
        // de cantidad, igual que el patrón de elegir_combo.html
        cajaCantidad.classList.remove('reserva-ee-hidden');

        // Si eligen 2x1 y la cantidad actual es impar, la ajustamos a la par más cercana
        const promo = promoSeleccionada();
        if (promo && promo.tipo === '2x1' && cantidad % 2 !== 0) {
            cantidad = Math.min(MAX_CANTIDAD, cantidad + 1);
        }
        actualizarResumen();
    }

    tarjetas.forEach(function (tarjeta) {
        tarjeta.addEventListener('click', function () {
            seleccionarTarjeta(tarjeta);
        });
    });

    // Si tocan directo el input de cupón, seleccionamos esa tarjeta también
    // (llamando a la función de arriba, no a un click() simulado)
    const inputCupon = document.getElementById('inputCupon');
    if (inputCupon) {
        inputCupon.addEventListener('focus', function () {
            seleccionarTarjeta(document.querySelector('.tarjeta-tipo-entrada[data-valor="cupon"]'));
        });
        // Evita que el click dentro del input dispare DE NUEVO el listener
        // de click del <label> que lo envuelve (quedaría duplicado, aunque
        // inofensivo — esto lo deja más prolijo y evita el "parpadeo")
        inputCupon.addEventListener('click', function (e) {
            e.stopPropagation();
        });
    }

    actualizarResumen();
})();
