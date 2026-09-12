// modificado: JS extraido del <script> inline de perfil.html. Las partes de "mostrar/ocultar
// contraseña" y "medidor de fuerza" que tenía este mismo bloque se movieron a archivos
// compartidos (password_toggle.js y password_strength.js) porque eran una copia casi idéntica
// de lo que ya tenía cambiar_password.html — acá solo queda lo específico de esta página:
// las pestañas (tabs) y la barra de progreso del Club Cine.
document.addEventListener('DOMContentLoaded', function () {
    // 1. Pestañas (Tabs)
    const tabs = document.querySelectorAll('.perfil-tab-btn');
    const sections = document.querySelectorAll('.perfil-tab-seccion');

    tabs.forEach(tab => {
        tab.addEventListener('click', function () {
            const target = tab.dataset.tab;
            if (!target) return; // Enlace al panel de administración staff

            tabs.forEach(t => t.classList.remove('activa'));
            sections.forEach(s => s.classList.remove('activa'));

            tab.classList.add('activa');
            const targetSec = document.getElementById(`tab-${target}`);
            if (targetSec) {
                targetSec.classList.add('activa');
            }
        });
    });

    // 2. Calcular Nivel del Club y Progreso
    // modificado: antes esta linea tenia "{{ total_reservas }}" interpolado directo por Django.
    // Un archivo .js estatico no pasa por el motor de templates, así que se lee desde el
    // data-total-reservas del contenedor (ver perfil.html) en vez de eso.
    const contenedor = document.querySelector('.perfil-contenedor');
    const totalReservas = parseInt(contenedor ? contenedor.dataset.totalReservas : '0', 10) || 0;
    const badgeEl = document.getElementById('tier-badge');
    const barEl = document.getElementById('tier-progress');
    const textEl = document.getElementById('tier-progress-text');

    if (badgeEl && barEl && textEl) {
        let tier = 'Bronce';
        let percent = 0;
        let text = '';

        if (totalReservas < 5) {
            tier = 'Bronce';
            percent = (totalReservas / 5) * 100;
            const faltantes = 5 - totalReservas;
            text = `${faltantes} reserva(s) para nivel Plata`;
            badgeEl.classList.add('bronce');
        } else if (totalReservas < 10) {
            tier = 'Plata';
            percent = ((totalReservas - 5) / 5) * 100;
            const faltantes = 10 - totalReservas;
            text = `${faltantes} reserva(s) para nivel Oro`;
            badgeEl.classList.add('plata');
        } else {
            tier = 'Oro';
            percent = 100;
            text = '¡Nivel máximo alcanzado!';
            badgeEl.classList.add('oro');
        }

        badgeEl.textContent = tier;
        barEl.style.width = `${percent}%`;
        textEl.textContent = text;
    }
});
