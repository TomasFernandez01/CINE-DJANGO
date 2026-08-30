// nuevo (Trailer): lazy-load del tráiler de YouTube en detalle_pelicula.html.
// Antes del click NO existe ningún <iframe> en el DOM — recién se crea acá,
// así que una visita normal a la página no descarga absolutamente nada de
// YouTube (ni el reproductor, ni el video). Solo se guarda un ID de texto
// de 11 caracteres en la base (ver Pelicula.trailer_youtube_id).
document.addEventListener('DOMContentLoaded', function () {
    const poster = document.getElementById('detallePosterTrailer');
    if (!poster) {
        return; // esta película no tiene trailer_youtube_id cargado
    }

    const btnPlay = poster.querySelector('.detalle-trailer-play-btn');
    if (!btnPlay) {
        return;
    }

    btnPlay.addEventListener('click', function () {
        const trailerId = poster.dataset.trailerId;
        if (!trailerId) {
            return;
        }

        const iframe = document.createElement('iframe');
        iframe.className = 'detalle-trailer-iframe';
        iframe.src = 'https://www.youtube.com/embed/' + encodeURIComponent(trailerId) + '?autoplay=1&rel=0';
        iframe.title = 'Tráiler';
        iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
        iframe.allowFullscreen = true;
        iframe.frameBorder = '0';

        // Reemplaza el poster+botón por el iframe (el poster queda oculto atrás,
        // no se destruye, así que si el usuario navega con el botón "atrás" del
        // navegador y vuelve, no hay ningún estado raro que reconstruir).
        poster.appendChild(iframe);
        poster.classList.add('detalle-poster-reproduciendo');
    });
});
