// nuevo (T14 - bug): reemplaza al <form> que estaba anidado dentro de
// <form id="formSalas"> (ver comentario en salas/lista.html). Arma el POST
// a mano con fetch() para no depender de un <form> real.
(function () {
    // El token CSRF se toma del <form id="formSalas"> que envuelve toda la
    // grilla — ya tiene {% csrf_token %} adentro, no hace falta duplicarlo.
    function getCsrfToken() {
        const input = document.querySelector('#formSalas [name=csrfmiddlewaretoken]');
        return input ? input.value : '';
    }

    document.querySelectorAll('[data-duplicar-sala]').forEach(function (wrap) {
        const boton = wrap.querySelector('.panelsalas-duplicar-btn');
        const select = wrap.querySelector('.panelsalas-duplicar-select');
        const url = wrap.dataset.url;

        boton.addEventListener('click', function () {
            if (!select.value) {
                select.reportValidity ? select.reportValidity() : alert('Elegí la sede destino.');
                return;
            }

            boton.disabled = true;
            boton.textContent = 'Duplicando…';

            const formData = new FormData();
            formData.append('sede_destino', select.value);

            fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfToken() },
                body: formData,
            })
                .then(function () {
                    // La vista redirige a salas_lista y deja el mensaje via
                    // messages framework — recargamos para verlo.
                    window.location.reload();
                })
                .catch(function () {
                    boton.disabled = false;
                    boton.textContent = 'Duplicar';
                    alert('No se pudo duplicar la sala. Probá de nuevo.');
                });
        });
    });
})();
