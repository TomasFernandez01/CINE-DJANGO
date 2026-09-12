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
// nuevo: modo "resumen" — en vez de un mensaje de texto plano, se puede pasar
// una lista con viñetas + un aviso destacado aparte (pensado para los
// modales de "eliminar" del panel, que muestran cuántas funciones/reservas/
// pagos se van a borrar en cascada):
//
//   window.mostrarModalConfirmacion({
//       titulo: 'Confirmar eliminación',
//       lineas: ['Sala A: 3 función(es), 12 reserva(s)', 'Sala B: 0 función(es), 0 reserva(s)'],
//       advertencia: 'Esta acción no se puede deshacer.',
//       textoConfirmar: 'Sí, eliminar definitivamente',
//       peligro: true
//   }).then(function (confirmado) { ... });
//
// Si no se pasa 'lineas', se usa 'mensaje' como antes (texto plano, con
// soporte para \n gracias a white-space:pre-line en el CSS).
//
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
        const listaEl        = document.getElementById('modalConfirmacionLista');
        const advertenciaEl  = document.getElementById('modalConfirmacionAdvertencia');
        const btnConfirmar   = document.getElementById('modalConfirmacionConfirmar');
        const btnCancelar    = document.getElementById('modalConfirmacionCancelar');

        const soloInformar = opciones.soloInformar === true;

        tituloEl.textContent  = opciones.titulo || 'Confirmar';

        // modificado: modo "resumen" — si viene opciones.lineas (array de
        // strings), se arma una lista con viñetas en vez de texto plano
        // pegado con \n. opciones.advertencia (opcional) se muestra aparte,
        // en un recuadro destacado, en vez de ir mezclada dentro del mismo
        // párrafo que el resumen. Antes eliminar_modal.js armaba todo esto
        // como un solo string con \n\n, y quedaba todo amontonado en un
        // párrafo de texto plano (aun con white-space:pre-line, es más
        // difícil de leer que una lista real).
        if (listaEl && Array.isArray(opciones.lineas) && opciones.lineas.length > 0) {
            mensajeEl.classList.add('oculto');
            mensajeEl.textContent = '';

            listaEl.innerHTML = '';
            opciones.lineas.forEach(function (linea) {
                const li = document.createElement('li');
                li.textContent = linea;
                listaEl.appendChild(li);
            });
            listaEl.classList.remove('oculto');
        } else {
            if (listaEl) {
                listaEl.classList.add('oculto');
                listaEl.innerHTML = '';
            }
            mensajeEl.classList.remove('oculto');
            mensajeEl.textContent = opciones.mensaje || '¿Confirmás esta acción?';
        }

        if (advertenciaEl) {
            if (opciones.advertencia) {
                advertenciaEl.textContent = '⚠️ ' + opciones.advertencia;
                advertenciaEl.classList.remove('oculto');
            } else {
                advertenciaEl.classList.add('oculto');
                advertenciaEl.textContent = '';
            }
        }

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
