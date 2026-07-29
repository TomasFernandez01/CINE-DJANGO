// modificado (Tanda B pagos): script movido desde procesar_pago.html (estaba inline)

function selectMetodo(metodo, elLabel) {
    document.querySelectorAll('.metodo-pago-card').forEach(function (l) {
        l.classList.remove('seleccionada');
    });
    if (elLabel) elLabel.classList.add('seleccionada');

    const datosTarjeta = document.getElementById('datosTarjeta');
    const esTarjeta = metodo === 'tarjeta_debito' || metodo === 'tarjeta_credito';
    datosTarjeta.classList.toggle('pago-datos-tarjeta-visible', esTarjeta);
    ['nombre_titular', 'numero_tarjeta', 'vencimiento', 'cvv'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.required = esTarjeta;
    });
}

// ===== AUTO-FORMATO TARJETA =====
document.getElementById('numero_tarjeta')?.addEventListener('input', function (e) {
    let v = e.target.value.replace(/\s/g, '');
    let f = v.match(/.{1,4}/g);
    e.target.value = f ? f.join(' ') : v;
});
document.getElementById('vencimiento')?.addEventListener('input', function (e) {
    let v = e.target.value.replace(/\D/g, '');
    e.target.value = v.length >= 2 ? v.slice(0, 2) + '/' + v.slice(2, 4) : v;
});
document.getElementById('cvv')?.addEventListener('input', function (e) {
    e.target.value = e.target.value.replace(/\D/g, '');
});

// ===== CONTADOR REGRESIVO =====
(function () {
    const el = document.getElementById('countdown');
    const container = document.getElementById('countdownContainer');
    const btn = document.getElementById('submitBtn');
    const form = document.getElementById('pagoForm');
    if (!el) return;
    let tiempo = parseInt(el.dataset.tiempo);

    function tick() {
        if (tiempo <= 0) {
            el.textContent = '00:00';
            container.classList.add('pago-countdown-expirado');
            if (btn) {
                btn.disabled = true;
                btn.classList.add('pago-btn-confirmar-deshabilitado');
                btn.innerHTML = '⏰ Tiempo Expirado';
            }
            if (form) form.classList.add('pago-form-deshabilitado');
            setTimeout(() => {
                alert('⏰ El tiempo de pago expiró. La reserva será cancelada automáticamente.');
                window.location.href = window.PAGO_URL_MIS_RESERVAS || '/';
            }, 1000);
            return;
        }
        const m = Math.floor(tiempo / 60), s = tiempo % 60;
        el.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        if (tiempo <= 180) container.classList.add('pago-countdown-urgente');
        tiempo--;
    }
    tick();
    const iv = setInterval(() => { tick(); if (tiempo < 0) clearInterval(iv); }, 1000);
})();
