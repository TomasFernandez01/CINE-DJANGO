// nuevo (T15 - QR oculto): toggle compartido entre comprobante_pago.html y
// detalle_reserva.html. El código de texto queda oculto por defecto (solo
// se ve la imagen del QR) — este botón lo revela para el caso en que el
// personal necesite tipearlo a mano en el Verificador QR del panel porque
// la cámara no pudo leer la imagen.
(function () {
    document.querySelectorAll('[data-qr-toggle]').forEach(function (boton) {
        // El código vive en el próximo elemento hermano (data-qr-codigo),
        // tal cual está armado en ambos templates.
        var codigoDiv = boton.nextElementSibling;
        if (!codigoDiv || !codigoDiv.hasAttribute('data-qr-codigo')) return;

        boton.addEventListener('click', function () {
            var oculto = codigoDiv.hasAttribute('hidden');
            if (oculto) {
                codigoDiv.removeAttribute('hidden');
                boton.textContent = 'Ocultar código';
            } else {
                codigoDiv.setAttribute('hidden', '');
                boton.textContent = '¿No se puede escanear? Mostrar código';
            }
        });
    });
})();
