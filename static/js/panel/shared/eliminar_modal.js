// nuevo: reemplaza la navegación a confirmar_eliminar.html (salas, funciones,
// combos, etc) por un modal, sin perder el resumen de lo que se va a borrar
// en cascada (funciones/reservas/pagos según la sección).
//
// Cómo funciona: cualquier <form data-eliminar-modal action="..."> que borra
// varios ítems seleccionados con checkboxes pasa a manejarse acá:
//   1. Al enviar el form, se intercepta y se hace un fetch() del mismo POST
//      con header X-Requested-With: XMLHttpRequest. La vista del panel
//      (panel/views/salas.py, funciones.py, promociones.py) detecta ese
//      header y en vez de renderizar confirmar_eliminar.html devuelve JSON:
//      { lineas: [...], advertencia: "..." }.
//   2. Con eso se arma el modal (mostrarModalConfirmacion), mismo mensaje
//      que antes mostraba la tabla de la página completa, ahora como texto.
//   3. Si confirman, se manda un segundo POST con confirmado=1 (igual que
//      hacía el botón "Sí, eliminar" de la página vieja) y se recarga la
//      lista para ver el resultado (toast de éxito incluido).
//
// Si el form NO tiene data-eliminar-modal, no se toca nada: sigue
// funcionando como antes (navegación normal a confirmar_eliminar.html).
// Esto es intencional como respaldo por si JS falla en algún punto.
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form[data-eliminar-modal]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const fd = new FormData(form);

            fetch(form.action, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                body: fd
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.error) {
                        return window.mostrarModalConfirmacion({
                            titulo: 'No se puede continuar',
                            mensaje: data.error,
                            textoConfirmar: 'Entendido',
                            soloInformar: true,
                            peligro: false
                        });
                    }

                    let mensaje = (data.lineas || []).join('\n');
                    if (data.advertencia) {
                        mensaje += (mensaje ? '\n\n' : '') + data.advertencia;
                    }

                    return window.mostrarModalConfirmacion({
                        titulo: 'Confirmar eliminación',
                        mensaje: mensaje || '¿Confirmás que querés eliminar los elementos seleccionados?',
                        textoConfirmar: 'Sí, eliminar definitivamente',
                        textoCancelar: 'Cancelar',
                        peligro: true
                    }).then(function (confirmado) {
                        if (!confirmado) return;

                        const fdConfirmar = new FormData(form);
                        fdConfirmar.append('confirmado', '1');

                        return fetch(form.action, { method: 'POST', body: fdConfirmar })
                            .then(function () { window.location.reload(); });
                    });
                })
                .catch(function () {
                    window.mostrarModalConfirmacion({
                        titulo: 'Error',
                        mensaje: 'No se pudo comunicar con el servidor. Intentá nuevamente.',
                        textoConfirmar: 'Entendido',
                        soloInformar: true,
                        peligro: false
                    });
                });
        });
    });
});
