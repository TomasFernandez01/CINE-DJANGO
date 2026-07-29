// nuevo: toggle del mapa de asientos de solo lectura en salas/lista_salas.html
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".salas-mapa-toggle-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            const salaId = btn.dataset.salaId;
            const panel = document.getElementById("salas-mapa-panel-" + salaId);
            if (!panel) return;

            const abierto = panel.classList.toggle("salas-mapa-abierto");
            btn.textContent = abierto ? "Ocultar mapa de asientos" : "Ver mapa de asientos";
        });
    });
});
