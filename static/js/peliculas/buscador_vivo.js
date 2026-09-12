// MEJORAS/REDISEÑO GEMINI: Buscador en vivo tipo Netflix (SPA) y filtros dinámicos por AJAX
document.addEventListener('DOMContentLoaded', function () {
    const inputBuscar = document.getElementById('buscar');
    const selectGenero = document.getElementById('genero');
    const selectClasificacion = document.getElementById('clasificacion');
    const gridContainer = document.getElementById('peliculas-grid-container');
    const hiddenFecha = document.getElementById('hidden-fecha');
    
    if (!inputBuscar || !gridContainer) return;

    let debounceTimeout = null;

    // Función principal para realizar el filtrado por AJAX
    function filtrarPeliculas() {
        const query = inputBuscar.value.trim();
        const genero = selectGenero ? selectGenero.value : '';
        const clasificacion = selectClasificacion ? selectClasificacion.value : '';
        const fecha = hiddenFecha ? hiddenFecha.value : '';

        // Construir los query params
        const params = new URLSearchParams();
        if (query) params.append('buscar', query);
        if (genero) params.append('genero', genero);
        if (clasificacion) params.append('clasificacion', clasificacion);
        if (fecha) params.append('fecha', fecha);
        params.append('ajax', 'true');

        // URL a consultar
        const url = window.location.pathname + '?' + params.toString();

        // Mostrar un loader sutil sobre el grid o esqueleto de carga
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
            
            // Re-vincular los eventos de paginación que se acaban de inyectar
            vincularPaginacion();
        })
        .catch(err => {
            console.error('Error al filtrar películas:', err);
            gridContainer.style.opacity = '1';
        });
    }

    // Escuchar el tecleo con un debounce de 250ms
    inputBuscar.addEventListener('input', function () {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(filtrarPeliculas, 250);
        
        // Sincronizar con el form si se llega a enviar por POST/GET tradicional
        const hiddenBuscar = document.getElementById('hidden-buscar');
        if (hiddenBuscar) hiddenBuscar.value = this.value;
    });

    // Escuchar el cambio en los select de Género y Clasificación
    if (selectGenero) {
        selectGenero.addEventListener('change', filtrarPeliculas);
    }
    if (selectClasificacion) {
        selectClasificacion.addEventListener('change', filtrarPeliculas);
    }

    // Interceptar clics en el carrusel de fechas para evitar recarga de página
    const carruselFechas = document.querySelector('.fechas-carrusel');
    if (carruselFechas) {
        carruselFechas.addEventListener('click', function (e) {
            const itemFecha = e.target.closest('.fecha-item');
            if (!itemFecha) return;

            e.preventDefault();

            // Determinar si ya estaba activa (toggle/deselección)
            const yaActiva = itemFecha.classList.contains('fecha-activa');
            
            // Limpiar clases activas en todas las fechas
            carruselFechas.querySelectorAll('.fecha-item').forEach(el => {
                el.classList.remove('fecha-activa');
            });

            if (yaActiva) {
                // Deseleccionar
                if (hiddenFecha) hiddenFecha.value = '';
            } else {
                // Seleccionar nueva
                itemFecha.classList.add('fecha-activa');
                // Obtener valor de la fecha desde el parámetro href
                const urlObj = new URL(itemFecha.href, window.location.origin);
                const valorFecha = urlObj.searchParams.get('fecha') || '';
                if (hiddenFecha) hiddenFecha.value = valorFecha;
            }

            filtrarPeliculas();
        });
    }

    // Interceptar clics en los enlaces de paginación dentro del grid
    function vincularPaginacion() {
        const paginacionLinks = gridContainer.querySelectorAll('.paginacion-link');
        paginacionLinks.forEach(link => {
            link.addEventListener('click', function (e) {
                e.preventDefault();
                const urlObj = new URL(this.href, window.location.origin);
                const page = urlObj.searchParams.get('page') || '1';
                
                // Actualizar la grilla enviando la página correcta
                const query = inputBuscar.value.trim();
                const genero = selectGenero ? selectGenero.value : '';
                const clasificacion = selectClasificacion ? selectClasificacion.value : '';
                const fecha = hiddenFecha ? hiddenFecha.value : '';

                const params = new URLSearchParams();
                if (query) params.append('buscar', query);
                if (genero) params.append('genero', genero);
                if (clasificacion) params.append('clasificacion', clasificacion);
                if (fecha) params.append('fecha', fecha);
                params.append('page', page);
                params.append('ajax', 'true');

                const url = window.location.pathname + '?' + params.toString();

                gridContainer.style.opacity = '0.5';

                fetch(url, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                })
                .then(response => response.text())
                .then(html => {
                    gridContainer.innerHTML = html;
                    gridContainer.style.opacity = '1';
                    
                    // Hacer scroll hacia arriba suavemente de la grilla al cambiar de página
                    gridContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    
                    vincularPaginacion();
                })
                .catch(err => {
                    console.error('Error en paginación AJAX:', err);
                    gridContainer.style.opacity = '1';
                });
            });
        });
    }

    // Ejecutar vinculación inicial de paginación
    vincularPaginacion();
});
