// MEJORAS/REDISEÑO GEMINI: Lógica interactiva para la vista de salas en dos columnas
document.addEventListener("DOMContentLoaded", function () {
    const tarjetasClickable = document.querySelectorAll(".salas-tarjeta-clickable");
    const placeholderMapa = document.getElementById("placeholder-mapa");
    const panelesMapas = document.querySelectorAll(".salas-mapa-panel-lateral");
    
    if (!tarjetasClickable.length) return;

    function activarSala(salaId) {
        // Deseleccionar todas las tarjetas
        tarjetasClickable.forEach(function (card) {
            card.classList.remove("seleccionada");
            const btn = card.querySelector(".salas-mapa-toggle-btn");
            if (btn) btn.textContent = "Ver mapa de asientos";
        });

        // Seleccionar tarjeta actual
        const tarjetaActual = document.querySelector(`.salas-tarjeta-clickable[data-sala-id="${salaId}"]`);
        if (tarjetaActual) {
            tarjetaActual.classList.add("seleccionada");
            const btn = tarjetaActual.querySelector(".salas-mapa-toggle-btn");
            if (btn) btn.textContent = "Viendo mapa...";
        }

        // Ocultar placeholder
        if (placeholderMapa) {
            placeholderMapa.style.display = "none";
        }

        // Ocultar todos los paneles de mapas y mostrar el seleccionado
        panelesMapas.forEach(function (panel) {
            panel.classList.remove("activo");
        });

        const panelActual = document.getElementById("salas-mapa-panel-" + salaId);
        if (panelActual) {
            panelActual.classList.add("activo");
        }
    }

    // Vincular clic tanto en la tarjeta completa como en el botón
    tarjetasClickable.forEach(function (tarjeta) {
        tarjeta.addEventListener("click", function (e) {
            const salaId = this.dataset.salaId;
            activarSala(salaId);
        });

        // Evitar doble evento si hacen click exactamente en el botón
        const btn = tarjeta.querySelector(".salas-mapa-toggle-btn");
        if (btn) {
            btn.addEventListener("click", function (e) {
                e.stopPropagation(); // Detener propagación hacia la tarjeta
                const salaId = tarjeta.dataset.salaId;
                activarSala(salaId);
            });
        }
    });
});
