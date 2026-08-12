// nuevo: modal de confirmación reutilizable, reemplaza a confirm() de JS
// (que se veía "roto" con el resto del estilo del sitio). Cualquier
// template puede usarlo así:
//
//   window.mostrarModalConfirmacion({
//       titulo: 'Confirmar reserva',
//       mensaje: 'Asientos: A1, A2\nTotal: $2400',
//       textoConfirmar: 'Confirmar',
//       textoCancelar: 'Volver',
//       peligro: false   // true = botón de confirmar en rojo (para acciones destructivas)
//   }).then(function (confirmado) {
//       if (confirmado) { /* seguir */ }
//   });
//
// nuevo: modo "solo informar" (un único botón, sin Cancelar) para avisos
// donde no hay una decisión real que tomar (ej: "el tiempo expiró"). Se
// activa con soloInformar: true. El fondo y la tecla Escape también
// resuelven la promesa en true (dado que no hay una acción de "cancelar"
// distinta a cerrar el aviso).
//
//   window.mostrarModalConfirmacion({
//       titulo: 'Tiempo expirado',
//       mensaje: 'El tiempo para completar la compra expiró.',
//       textoConfirmar: 'Entendido',
//       soloInformar: true
//   }).then(function () { /* redirigir, etc */ });
//
// El modal en sí (el HTML) vive una sola vez en base.html, así que no hay
// que repetirlo en cada template — esta función solo lo completa y lo
// muestra/oculta.
window.mostrarModalConfirmacion = function (opciones) {
    opciones = opciones || {};

    return new Promise(function (resolve) {
        const modal = document.getElementById('modalConfirmacion');
        if (!modal) {
            // Si por algún motivo el modal no está en el HTML (base.html
            // no se cargó bien), no rompemos el flujo: caemos al confirm()
            // nativo como respaldo.
            resolve(window.confirm(opciones.mensaje || '¿Confirmás esta acción?'));
            return;
        }

        const fondo         = modal.querySelector('[data-modal-cerrar]');
        const tituloEl       = document.getElementById('modalConfirmacionTitulo');
        const mensajeEl      = document.getElementById('modalConfirmacionMensaje');
        const btnConfirmar   = document.getElementById('modalConfirmacionConfirmar');
        const btnCancelar    = document.getElementById('modalConfirmacionCancelar');

        const soloInformar = opciones.soloInformar === true;

        tituloEl.textContent  = opciones.titulo || 'Confirmar';
        mensajeEl.textContent = opciones.mensaje || '¿Confirmás esta acción?';
        btnConfirmar.textContent = opciones.textoConfirmar || (soloInformar ? 'Entendido' : 'Confirmar');
        btnCancelar.textContent  = opciones.textoCancelar || 'Cancelar';
        btnConfirmar.classList.toggle('modal-confirmacion-btn--peligro', opciones.peligro !== false);
        // nuevo: en modo "solo informar" se oculta el botón Cancelar, no
        // tiene sentido ofrecer una segunda opción cuando no hay nada que
        // cancelar (ej: aviso de tiempo expirado).
        btnCancelar.classList.toggle('oculto', soloInformar);

        function cerrar(resultado) {
            modal.classList.add('oculto');
            modal.setAttribute('aria-hidden', 'true');
            document.removeEventListener('keydown', onEsc);
            btnConfirmar.removeEventListener('click', onConfirmar);
            btnCancelar.removeEventListener('click', onCancelar);
            fondo.removeEventListener('click', onFondo);
            resolve(resultado);
        }
        function onConfirmar() { cerrar(true); }
        function onCancelar() { cerrar(false); }
        // En modo "solo informar" no hay cancelación real: cerrar por
        // fondo/Escape equivale a "Entendido" (resuelve true).
        function onFondo() { cerrar(soloInformar ? true : false); }
        function onEsc(e) { if (e.key === 'Escape') cerrar(soloInformar ? true : false); }

        btnConfirmar.addEventListener('click', onConfirmar);
        btnCancelar.addEventListener('click', onCancelar);
        fondo.addEventListener('click', onFondo);
        document.addEventListener('keydown', onEsc);

        modal.classList.remove('oculto');
        modal.setAttribute('aria-hidden', 'false');
        (soloInformar ? btnConfirmar : btnCancelar).focus();
    });
};
