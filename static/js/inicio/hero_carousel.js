// nuevo: rota automaticamente los posters de fondo del hero (fade cada 5s)
// Si no hay ningun .hero-slide en la pagina (no se cargaron posters todavia), no hace nada.
document.addEventListener('DOMContentLoaded', function () {
    const slides = document.querySelectorAll('.hero-slide');
    if (slides.length <= 1) {
        return; // 0 o 1 poster: nada que rotar
    }

    let indiceActual = 0;
    const INTERVALO_MS = 5000;

    setInterval(function () {
        slides[indiceActual].classList.remove('activa');
        indiceActual = (indiceActual + 1) % slides.length;
        slides[indiceActual].classList.add('activa');
    }, INTERVALO_MS);
});
