// MEJORAS/REDISEÑO GEMINI: Buscador en vivo y filtrado AJAX para Funciones
document.addEventListener('DOMContentLoaded', function () {
    const inputBuscar = document.getElementById('buscar-funciones');
    const selectSala = document.getElementById('filtro-sala');
    const selectFechaRapida = document.getElementById('filtro-fecha-rapida');
    const gridContainer = document.getElementById('funciones-grid-container');
    const hiddenFecha = document.getElementById('hidden-fecha-funciones');
    
    if (!inputBuscar || !gridContainer) return;

    let debounceTimeout = null;

    function filtrarFunciones() {
        const query = inputBuscar.value.trim();
        const sala = selectSala ? selectSala.value : '';
        // Si el select de fecha rápida tiene valor, sobreescribe la fecha del carrusel
        let fecha = hiddenFecha ? hiddenFecha.value : '';
        if (selectFechaRapida && selectFechaRapida.value) {
            fecha = selectFechaRapida.value;
        }

        const params = new URLSearchParams();
        if (query) params.append('buscar', query);
        if (sala) params.append('sala', sala);
        if (fecha) params.append('fecha', fecha);
        params.append('ajax', 'true');

        const url = window.location.pathname + '?' + params.toString();

        gridContainer.style.opacity = '0.5';
        gridContainer.style.transition = 'opacity 0.15s ease';

        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.text())
        .then(html => {
            gridContainer.innerHTML = html;
            gridContainer.style.opacity = '1';
        })
        .catch(err => {
            console.error('Error al filtrar funciones:', err);
            gridContainer.style.opacity = '1';
        });
    }

    inputBuscar.addEventListener('input', function () {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(filtrarFunciones, 250);
        
        const hiddenBuscar = document.getElementById('hidden-buscar-funciones');
        if (hiddenBuscar) hiddenBuscar.value = this.value;
    });

    if (selectSala) {
        selectSala.addEventListener('change', filtrarFunciones);
    }

    if (selectFechaRapida) {
        selectFechaRapida.addEventListener('change', function () {
            // Si eligen una fecha rápida (Hoy, Mañana, Semana), deseleccionamos el carrusel de fechas para no confundir
            if (this.value) {
                const carruselFechas = document.querySelector('.fechas-carrusel');
                if (carruselFechas) {
                    carruselFechas.querySelectorAll('.fecha-item').forEach(el => {
                        el.classList.remove('fecha-activa');
                    });
                }
                if (hiddenFecha) hiddenFecha.value = '';
            }
            filtrarFunciones();
        });
    }

    // Interceptar clics en el carrusel de fechas
    const carruselFechas = document.querySelector('.fechas-carrusel');
    if (carruselFechas) {
        carruselFechas.addEventListener('click', function (e) {
            const itemFecha = e.target.closest('.fecha-item');
            if (!itemFecha) return;

            e.preventDefault();

            // Si se selecciona el carrusel, reseteamos el select de fecha rápida
            if (selectFechaRapida) selectFechaRapida.value = '';

            const yaActiva = itemFecha.classList.contains('fecha-activa');
            
            carruselFechas.querySelectorAll('.fecha-item').forEach(el => {
                el.classList.remove('fecha-activa');
            });

            if (yaActiva) {
                if (hiddenFecha) hiddenFecha.value = '';
            } else {
                itemFecha.classList.add('fecha-activa');
                const urlObj = new URL(itemFecha.href, window.location.origin);
                const valorFecha = urlObj.searchParams.get('fecha') || '';
                if (hiddenFecha) hiddenFecha.value = valorFecha;
            }

            filtrarFunciones();
        });
    }
});
