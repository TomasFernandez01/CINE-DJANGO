(function() {
    const el = document.getElementById('countdown');
    const container = document.getElementById('countdownContainer');
    const pagarBtn = document.getElementById('pagarBtn');
    if (!el) return;
    let tiempo = parseInt(el.dataset.tiempo);
    function tick() {
        if (tiempo <= 0) {
            el.textContent = '00:00';
            container.style.background = 'linear-gradient(135deg, #6c757d 0%, #495057 100%)';
            if (pagarBtn) {
                pagarBtn.style.backgroundColor = '#6c757d';
                pagarBtn.style.pointerEvents = 'none';
                pagarBtn.innerHTML = '⏰ Tiempo Expirado';
            }
            setTimeout(() => { alert('⏰ El tiempo de pago expiró.'); window.location.reload(); }, 1000);
            return;
        }
        const m = Math.floor(tiempo / 60), s = tiempo % 60;
        el.textContent = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
        if (tiempo <= 180) container.style.background = 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)';
        tiempo--;
    }
    tick();
    const iv = setInterval(() => { tick(); if (tiempo < 0) clearInterval(iv); }, 1000);
})();
