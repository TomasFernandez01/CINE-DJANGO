// Cuenta regresiva por cada reserva pendiente, sin recargar toda la página.
// Antes esto era un location.reload() cada 30s (perdía el scroll y refrescaba
// todo de golpe). Ahora cada contador descuenta solo en el navegador a partir
// del valor que ya vino calculado del server (data-segundos), y solo se hace
// UN reload cuando una reserva puntual llega a 0 (para reflejar que expiró).
(function () {
    const contadores = document.querySelectorAll('[id^="contador-"]');
    if (!contadores.length) return;

    let huboExpiracion = false;

    function formatoMMSS(segundos) {
        const m = Math.floor(segundos / 60);
        const s = segundos % 60;
        return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    contadores.forEach(el => {
        let segundos = parseInt(el.dataset.segundos, 10);
        if (isNaN(segundos)) return;

        const intervalo = setInterval(() => {
            segundos -= 1;
            if (segundos <= 0) {
                clearInterval(intervalo);
                // BUGFIX: antes decía '⏰ Expirado' / '⏰ MM:SS', un formato
                // distinto al que renderiza el server ("Tiempo restante:
                // MM:SS"), dando el efecto de que el contador "cambiaba de
                // golpe" apenas corría el primer tick (y reintroducía un
                // emoji que el resto del panel ya había sacado). Mismo
                // formato en todo momento, sin salto visual.
                el.textContent = 'Expirado';
                huboExpiracion = true;
                // Un solo reload, con un pequeño margen para que el comando
                // de cancelación / la vista alcancen a actualizar el estado real.
                setTimeout(() => location.reload(), 2000);
            } else {
                el.textContent = `Tiempo restante: ${formatoMMSS(segundos)}`;
            }
        }, 1000);
    });
})();

// modificado: filtros (antes onchange="...submit()" inline en cada checkbox)
(function () {
    const form = document.getElementById('filtrosForm');
    if (!form) return;
    form.querySelectorAll('input[type="checkbox"]').forEach(function (checkbox) {
        checkbox.addEventListener('change', function () {
            form.submit();
        });
    });
})();

// modificado (punto 4/2 de revisión): confirmaciones de cancelar/eliminar
// con el modal compartido en vez de confirm() nativo. data-confirm sigue
// siendo el mensaje (ya lo traía el template), y data-confirm-titulo /
// data-confirm-texto son opcionales para personalizar el título y el
// texto del botón según la acción (cancelar reserva vs. eliminar del historial).
(function () {
    document.querySelectorAll('[data-confirm]').forEach(function (enlace) {
        enlace.addEventListener('click', function (e) {
            e.preventDefault();
            window.mostrarModalConfirmacion({
                titulo: enlace.dataset.confirmTitulo || 'Confirmar',
                mensaje: enlace.dataset.confirm,
                textoConfirmar: enlace.dataset.confirmTexto || 'Sí, continuar',
                textoCancelar: 'Volver',
                peligro: true
            }).then(function (confirmado) {
                if (confirmado) window.location.href = enlace.href;
            });
        });
    });
})();
