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
                el.textContent = '⏰ Expirado';
                huboExpiracion = true;
                // Un solo reload, con un pequeño margen para que el comando
                // de cancelación / la vista alcancen a actualizar el estado real.
                setTimeout(() => location.reload(), 2000);
            } else {
                el.textContent = `⏰ ${formatoMMSS(segundos)}`;
            }
        }, 1000);
    });
})();
