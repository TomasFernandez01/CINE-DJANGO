// Alertas según estado seleccionado
const estadoSelect = document.getElementById('id_estado');
const alertaDiv    = document.getElementById('alertaEstado');

const alertas = {
    'confirmada': { color:'#d4edda', border:'#27ae60', texto:'✅ Confirmar la reserva. Asegurate de que el pago esté registrado.' },
    'cancelada':  { color:'#f8d7da', border:'#e74c3c', texto:'⚠️ Cancelar la reserva liberará los asientos para otros usuarios.' },
    'expirada':   { color:'#e2e3e5', border:'#6c757d', texto:'ℹ️ Marcar como expirada. La función ya debería haber pasado.' },
    'pendiente':  { color:'#fff3cd', border:'#f39c12', texto:'⏳ Reserva pendiente de pago. El contador estará activo.' },
};

function actualizarAlerta() {
    const estado = estadoSelect.value;
    const alerta = alertas[estado];
    if (alerta) {
        alertaDiv.innerHTML = `
            <div style="background:${alerta.color}; border-left:3px solid ${alerta.border};
                        padding:0.65rem 0.85rem; border-radius:6px; font-size:0.825rem;">
                ${alerta.texto}
            </div>`;
    } else {
        alertaDiv.innerHTML = '';
    }
}

estadoSelect?.addEventListener('change', actualizarAlerta);
actualizarAlerta();

// Extender tiempo de pago
function extenderTiempo(minutos) {
    const input = document.getElementById('id_fecha_limite_pago');
    if (!input) return;

    const valorActual = input.value;
    let base = valorActual
        ? new Date(valorActual)
        : new Date();

    // Si la fecha ya pasó, usar ahora como base
    if (base < new Date()) base = new Date();

    base.setMinutes(base.getMinutes() + minutos);

    // Formatear para datetime-local: YYYY-MM-DDTHH:MM
    const pad = n => String(n).padStart(2, '0');
    const y   = base.getFullYear();
    const mo  = pad(base.getMonth() + 1);
    const d   = pad(base.getDate());
    const h   = pad(base.getHours());
    const mi  = pad(base.getMinutes());

    input.value = `${y}-${mo}-${d}T${h}:${mi}`;
}

// Copiar asiento al campo de texto
function copiarAsiento(asiento) {
    const input = document.getElementById('id_asientos_seleccionados');
    if (!input) return;
    const actual = input.value.trim();
    const lista  = actual ? actual.split(',').map(s => s.trim()).filter(Boolean) : [];
    if (!lista.includes(asiento)) {
        lista.push(asiento);
        input.value = lista.join(',');
    }
}
