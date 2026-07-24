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

// MODIFICACION GEMINI: Consulta dinamica de margen de tiempo entre funciones del mismo dia
function consultarCronograma() {
    const salaId = salaSelect?.value;
    const fechaHoraVal = fechaInput?.value;
    const cronogramaCard = document.getElementById('cronogramaCard');
    const cronogramaLista = document.getElementById('cronograma-lista');

    if (!salaId || !fechaHoraVal || !cronogramaCard || !cronogramaLista) {
        if (cronogramaCard) cronogramaCard.style.display = 'none';
        return;
    }

    // Extraer solo la fecha YYYY-MM-DD
    const fecha = fechaHoraVal.substring(0, 10);

    fetch(`/panel/funciones/margen-tiempo/?sala_id=${salaId}&fecha=${fecha}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                cronogramaCard.style.display = 'none';
                return;
            }

            cronogramaLista.innerHTML = '';
            if (data.funciones && data.funciones.length > 0) {
                data.funciones.forEach(func => {
                    const item = document.createElement('div');
                    item.style.padding = '0.5rem';
                    item.style.background = '#f8f9fa';
                    item.style.borderLeft = '4px solid #f39c12';
                    item.style.borderRadius = '4px';
                    item.style.display = 'flex';
                    item.style.justifyContent = 'space-between';
                    item.style.alignItems = 'center';
                    
                    item.innerHTML = `
                        <div>
                            <strong>${func.pelicula}</strong>
                        </div>
                        <div style="font-weight: 600; color: #555;">
                            ⏰ ${func.inicio} a ${func.fin} <span style="font-size: 0.75rem; font-weight: normal; color: #999;">(${func.duracion} min)</span>
                        </div>
                    `;
                    cronogramaLista.appendChild(item);
                });
            } else {
                const item = document.createElement('div');
                item.style.padding = '0.5rem';
                item.style.color = '#27ae60';
                item.style.fontWeight = '600';
                item.innerHTML = '✅ No hay funciones programadas para este día en esta sala. Horario totalmente libre.';
                cronogramaLista.appendChild(item);
            }
            cronogramaCard.style.display = 'block';
        })
        .catch(err => {
            console.error('Error al consultar cronograma:', err);
            cronogramaCard.style.display = 'none';
        });
}

pelSelect?.addEventListener('change', actualizarPreview);
salaSelect?.addEventListener('change', function() {
    actualizarPreview();
    consultarCronograma();
});
fechaInput?.addEventListener('change', function() {
    actualizarPreview();
    consultarCronograma();
});
precioInput?.addEventListener('input', actualizarPreview);

// Inicializar al cargar
actualizarPreview();
consultarCronograma();
