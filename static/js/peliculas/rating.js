// modificado: JS extraido de detalle_pelicula.html (estaba inline dentro de un <script>)
// Widget de estrellas interactivo para calificar una pelicula (formulario "Calificar esta pelicula")
document.addEventListener("DOMContentLoaded", function () {
    const estrellas = document.querySelectorAll(".estrella-btn");
    const inputPuntuacion = document.getElementById("inputPuntuacion");

    if (estrellas.length > 0 && inputPuntuacion) {
        function pintarEstrellas(valor) {
            estrellas.forEach((est) => {
                const estVal = parseInt(est.dataset.valor);
                if (estVal <= valor) {
                    est.textContent = "★";
                    est.classList.add("detalle-rating-estrella-activa"); // modificado: antes era est.style.color inline
                } else {
                    est.textContent = "☆";
                    est.classList.remove("detalle-rating-estrella-activa"); // modificado: antes era est.style.color inline
                }
            });
        }

        estrellas.forEach((est) => {
            est.addEventListener("click", function () {
                const valor = parseInt(this.dataset.valor);
                inputPuntuacion.value = valor;
                pintarEstrellas(valor);
            });

            est.addEventListener("mouseover", function () {
                const valor = parseInt(this.dataset.valor);
                pintarEstrellas(valor);
            });

            est.addEventListener("mouseout", function () {
                const valor = parseInt(inputPuntuacion.value) || 0;
                pintarEstrellas(valor);
            });
        });
    }
});
