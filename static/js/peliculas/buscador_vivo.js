// nuevo: buscador en vivo de la cartelera (autocompletado), JS puro con fetch() y debounce.
// Mientras el usuario escribe o borra en #buscar, consulta peliculas:buscar_vivo y pinta
// un dropdown de sugerencias abajo del input, sin recargar la pagina.

document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('buscar');
    const dropdown = document.getElementById('buscar-sugerencias');
    if (!input || !dropdown) {
        return;
    }

    const URL_BUSCAR_VIVO = input.dataset.urlBuscarVivo;
    let temporizador = null;

    function ocultarDropdown() {
        dropdown.innerHTML = '';
        dropdown.style.display = 'none';
    }

    function pintarResultados(resultados) {
        if (!resultados.length) {
            dropdown.innerHTML = '<div class="buscar-sugerencia-vacio">Sin coincidencias</div>';
            dropdown.style.display = 'block';
            return;
        }

        dropdown.innerHTML = resultados.map(function (p) {
            const posterHtml = p.poster_url
                ? '<img src="' + p.poster_url + '" alt="">'
                : '<div class="buscar-sugerencia-sinposter">🎬</div>';
            return (
                '<a class="buscar-sugerencia-item" href="' + p.url + '">' +
                    posterHtml +
                    '<div>' +
                        '<div class="buscar-sugerencia-titulo">' + p.titulo + '</div>' +
                        (p.genero ? '<div class="buscar-sugerencia-genero">' + p.genero + '</div>' : '') +
                    '</div>' +
                '</a>'
            );
        }).join('');
        dropdown.style.display = 'block';
    }

    input.addEventListener('input', function () {
        const consulta = input.value.trim();

        clearTimeout(temporizador);

        if (consulta.length < 2) {
            ocultarDropdown();
            return;
        }

        // debounce: espera 300ms de inactividad antes de consultar al servidor
        temporizador = setTimeout(function () {
            fetch(URL_BUSCAR_VIVO + '?q=' + encodeURIComponent(consulta))
                .then(function (resp) { return resp.json(); })
                .then(function (data) { pintarResultados(data.resultados); })
                .catch(function () { ocultarDropdown(); });
        }, 300);
    });

    // cierra el dropdown si se hace click afuera
    document.addEventListener('click', function (evento) {
        if (!dropdown.contains(evento.target) && evento.target !== input) {
            ocultarDropdown();
        }
    });
});
