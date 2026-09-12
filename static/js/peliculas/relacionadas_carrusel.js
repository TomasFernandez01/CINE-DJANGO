// nuevo: flechas de scroll horizontal para el carrusel de "también en cartelera"
// (detalle_pelicula.html). Mismo patrón que static/js/shared/fechas_carrusel.js,
// pero como archivo propio en vez de reutilizar ese — las clases de acá
// (.relacionadas-carrusel-wrap / .relacionadas-carrusel) son de películas
// relacionadas, no de fechas, así que conviene no mezclarlas bajo el mismo
// selector genérico aunque la lógica sea idéntica.
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.relacionadas-carrusel-wrap').forEach(function (wrap) {
        const carrusel = wrap.querySelector('.relacionadas-carrusel');
        const btnPrev = wrap.querySelector('.relacionadas-flecha-prev');
        const btnNext = wrap.querySelector('.relacionadas-flecha-next');
        if (!carrusel || !btnPrev || !btnNext) {
            return;
        }

        const DESPLAZAMIENTO = 340; // px por click de flecha (~2 posters de 160px + gap)

        function actualizarEstadoFlechas() {
            btnPrev.disabled = carrusel.scrollLeft <= 0;
            btnNext.disabled = carrusel.scrollLeft + carrusel.clientWidth >= carrusel.scrollWidth - 1;
        }

        btnPrev.addEventListener('click', function () {
            carrusel.scrollBy({ left: -DESPLAZAMIENTO, behavior: 'smooth' });
        });

        btnNext.addEventListener('click', function () {
            carrusel.scrollBy({ left: DESPLAZAMIENTO, behavior: 'smooth' });
        });

        carrusel.addEventListener('scroll', actualizarEstadoFlechas);
        actualizarEstadoFlechas();
    });
});
