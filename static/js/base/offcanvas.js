// nuevo: apertura/cierre del offcanvas de login / cuenta, vanilla JS (sin Bootstrap),
// mismo patrón que toast.js. Se abre desde el botón/avatar del nav (id="offcanvasAbrir")
// y se cierra con la X, clickeando el overlay, o con la tecla Escape.
document.addEventListener('DOMContentLoaded', function () {
    const abrirBtn = document.getElementById('offcanvasAbrir');
    const cerrarBtn = document.getElementById('offcanvasCerrar');
    const panel = document.getElementById('offcanvasPanel');
    const overlay = document.getElementById('offcanvasOverlay');

    if (!abrirBtn || !panel || !overlay) {
        return;
    }

    function abrir() {
        panel.classList.add('activo');
        overlay.classList.add('activo');
        panel.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
    }

    function cerrar() {
        panel.classList.remove('activo');
        overlay.classList.remove('activo');
        panel.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
    }

    abrirBtn.addEventListener('click', abrir);
    if (cerrarBtn) {
        cerrarBtn.addEventListener('click', cerrar);
    }
    overlay.addEventListener('click', cerrar);
    document.addEventListener('keydown', function (evento) {
        if (evento.key === 'Escape') {
            cerrar();
        }
    });
});
