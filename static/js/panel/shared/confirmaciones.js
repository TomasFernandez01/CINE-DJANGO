// nuevo: handler genérico para el Panel. Cualquier <a> o <button> con
// data-confirm="mensaje" usa el modal compartido (window.mostrarModalConfirmacion,
// definido en static/js/shared/modal_confirmacion.js) en vez de confirm()
// nativo del navegador. Se engancha una sola vez acá (base_panel.html), así
// que cualquier template nuevo del Panel puede sumar data-confirm sin tener
// que escribir JS propio.
//
// Atributos opcionales:
//   data-confirm-titulo   -> título del modal (default: "Confirmar")
//   data-confirm-texto    -> texto del botón confirmar (default: "Confirmar")
//   data-confirm-cancelar -> texto del botón cancelar (default: "Cancelar")
//   data-confirm-peligro="false" -> botón de confirmar NO rojo (por defecto es rojo)
//
// Funciona tanto en <a href="..."> (navega si confirman) como en <button>
// dentro de un <form> (hace form.submit() si confirman).
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-confirm]').forEach(function (el) {
        el.addEventListener('click', function (e) {
            e.preventDefault();
            window.mostrarModalConfirmacion({
                titulo: el.dataset.confirmTitulo || 'Confirmar',
                mensaje: el.dataset.confirm,
                textoConfirmar: el.dataset.confirmTexto || 'Confirmar',
                textoCancelar: el.dataset.confirmCancelar || 'Cancelar',
                peligro: el.dataset.confirmPeligro !== 'false'
            }).then(function (confirmado) {
                if (!confirmado) return;
                if (el.tagName === 'A') {
                    window.location.href = el.href;
                } else if (el.form) {
                    el.form.submit();
                }
            });
        });
    });
});
