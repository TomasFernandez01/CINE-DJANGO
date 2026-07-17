// nuevo: flechas de scroll horizontal para el carrusel de fechas (compartido entre peliculas y salas)
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.fechas-carrusel-wrap').forEach(function (wrap) {
        const carrusel = wrap.querySelector('.fechas-carrusel');
        const btnPrev = wrap.querySelector('.fecha-flecha-prev');
        const btnNext = wrap.querySelector('.fecha-flecha-next');
        if (!carrusel || !btnPrev || !btnNext) {
            return;
        }

        const DESPLAZAMIENTO = 300; // px por click de flecha

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
