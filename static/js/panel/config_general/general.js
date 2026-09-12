// nuevo (Hilo 1 - Tanda D): muestra/oculta los campos de SMTP según el modo de
// envío de email elegido - no tiene sentido pedir host/puerto/usuario si está
// en modo "Consola".
(function () {
    const selectBackend = document.getElementById('id_email_backend');
    const camposSmtp = document.getElementById('panelconfig-smtp-campos');
    if (!selectBackend || !camposSmtp) return;

    function actualizar() {
        camposSmtp.classList.toggle('panelconfig-oculto', selectBackend.value !== 'smtp');
    }

    selectBackend.addEventListener('change', actualizar);
    actualizar();
})();
