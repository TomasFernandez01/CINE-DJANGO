// Preview dinámico
const pelSelect   = document.getElementById('id_pelicula');
const salaSelect  = document.getElementById('id_sala');
const fechaInput  = document.getElementById('id_fecha_hora');
const precioInput = document.getElementById('id_precio');

function actualizarPreview() {
    const pelOpt  = pelSelect?.options[pelSelect.selectedIndex];
    const salaOpt = salaSelect?.options[salaSelect.selectedIndex];
    const fecha   = fechaInput?.value;
    const precio  = precioInput?.value;

    document.getElementById('prev-pelicula').textContent =
        (pelOpt && pelSelect.value) ? pelOpt.text : '—';
    document.getElementById('prev-sala').textContent =
        (salaOpt && salaSelect.value) ? salaOpt.text : '—';
    document.getElementById('prev-fecha').textContent = fecha
        ? new Date(fecha).toLocaleString('es-AR', {
            day:'2-digit', month:'2-digit', year:'numeric',
            hour:'2-digit', minute:'2-digit'
          })
        : '—';
    document.getElementById('prev-precio').textContent =
        precio ? `$${parseFloat(precio).toFixed(0)}` : '—';
}

pelSelect?.addEventListener('change', actualizarPreview);
salaSelect?.addEventListener('change', actualizarPreview);
fechaInput?.addEventListener('change', actualizarPreview);
precioInput?.addEventListener('input', actualizarPreview);

actualizarPreview();
