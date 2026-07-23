// modificado: extraído del <script> inline de detalle_reserva.html.
// El código QR ahora se lee desde el atributo data-codigo del propio
// <img id="qrImage">, en vez de venir embebido en un <script> con
// el valor de Django escrito directo en el JS.
(function () {
    const qrImage = document.getElementById('qrImage');
    if (!qrImage) return;

    const codigo = qrImage.dataset.codigo;
    if (!codigo) return;

    QRCode.toDataURL(codigo, { width: 220, margin: 2 }).then(function (url) {
        qrImage.src = url;
    }).catch(function (err) {
        console.error('Error generando QR:', err);
    });
})();
