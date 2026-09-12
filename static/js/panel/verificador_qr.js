// modificado: JS extraído de panel/verificador_qr.html (estaba inline). Las URLs de Django
// (verificar_qr_api, marcar_qr_escaneado) y el username del staff logueado no se pueden
// resolver desde un .js estático, así que se leen desde data-attributes del contenedor
// .panelqr-wrap (mismo patrón que ya se usaba en pagos/procesar_pago.js).
const panelqrWrap = document.querySelector('.panelqr-wrap');
const URL_VERIFICAR_QR = panelqrWrap.dataset.urlVerificar;
const URL_MARCAR_QR = panelqrWrap.dataset.urlMarcar;
const QR_USERNAME = panelqrWrap.dataset.username;

let html5QrCode = null;
let historialItems = [];

async function verificarCodigo() {
    const input = document.getElementById('codigoQR');
    const codigo = input.value.trim();
    if (!codigo) { mostrarStatus('Ingresá un código', '#f39c12'); return; }

    mostrarStatus('Verificando...', '#3498db');

    try {
        const fd = new FormData();
        fd.append('codigo_qr', codigo);

        const res = await fetch(URL_VERIFICAR_QR, {
            method: 'POST', body: fd
        });
        const data = await res.json();

        if (data.success && data.valido) {
            mostrarResultadoValido(data.reserva, codigo);
            agregarHistorial(codigo, data.reserva, true);
        } else {
            mostrarResultadoInvalido(data.error || 'Código inválido', data);
            agregarHistorial(codigo, null, false, data.error);
        }

        input.value = '';
        input.focus();

    } catch (e) {
        mostrarStatus('Error de conexión', '#e74c3c');
    }
}

function mostrarResultadoValido(reserva, codigo) {
    mostrarStatus('✅ Código Válido — Listo para ingresar', '#27ae60');
    const r = document.getElementById('resultado');
    r.style.display = 'block';
    r.innerHTML = `
        <div class="panelqr-resultado-ok">
            <h2 class="panelqr-resultado-ok-titulo">
                ✅ ENTRADA VÁLIDA
            </h2>
            <div class="panelqr-resultado-datos-box">
                <div class="panelqr-resultado-datos-grid">
                    <div>
                        <div class="panelqr-dato-label">Película</div>
                        <div class="panelqr-dato-valor-grande">${reserva.pelicula}</div>
                    </div>
                    <div>
                        <div class="panelqr-dato-label">Sala</div>
                        <div class="panelqr-dato-valor">${reserva.sala}</div>
                    </div>
                    <div>
                        <div class="panelqr-dato-label">Fecha y Hora</div>
                        <div class="panelqr-dato-valor">${reserva.fecha_hora}</div>
                    </div>
                    <div>
                        <div class="panelqr-dato-label">Entradas</div>
                        <div class="panelqr-dato-valor">${reserva.cantidad_entradas}</div>
                    </div>
                    ${reserva.asientos ? `
                    <div class="panelqr-dato-full">
                        <div class="panelqr-dato-label">Asientos</div>
                        <div class="panelqr-dato-valor">${reserva.asientos}</div>
                    </div>` : ''}
                    <div>
                        <div class="panelqr-dato-label">Usuario</div>
                        <div>${reserva.usuario}</div>
                    </div>
                    <div>
                        <div class="panelqr-dato-label">Código</div>
                        <div class="panelqr-dato-mono">${reserva.codigo}</div>
                    </div>
                </div>
            </div>
            <button onclick="marcarComoEscaneado('${codigo}')" class="panelqr-btn-confirmar">
                ✅ Confirmar Ingreso
            </button>
        </div>`;
    r.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function mostrarResultadoInvalido(mensaje, data) {
    mostrarStatus('❌ Código No Válido', '#e74c3c');
    const r = document.getElementById('resultado');
    r.style.display = 'block';
    r.innerHTML = `
        <div class="panelqr-resultado-error">
            <h2 class="panelqr-resultado-error-titulo">❌ ENTRADA NO VÁLIDA</h2>
            <p class="panelqr-resultado-error-msg">${mensaje}</p>
            ${data.ya_escaneado && data.fecha_escaneo
                ? `<p class="panelqr-resultado-error-fecha">
                    Escaneado el: ${new Date(data.fecha_escaneo).toLocaleString('es-AR')}</p>`
                : ''}
        </div>`;
    r.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function marcarComoEscaneado(codigo) {
    mostrarStatus('Registrando ingreso...', '#3498db');
    try {
        const fd = new FormData();
        fd.append('codigo_qr', codigo);
        fd.append('usuario', QR_USERNAME);

        const res = await fetch(URL_MARCAR_QR, {
            method: 'POST', body: fd
        });
        const data = await res.json();

        if (data.success) {
            mostrarStatus('✅ Ingreso Registrado Correctamente', '#27ae60');
            document.getElementById('resultado').innerHTML = `
                <div class="panelqr-registrado-box">
                    <h2 class="panelqr-registrado-titulo">
                        ✅ Ingreso Registrado
                    </h2>
                    <p class="panelqr-registrado-texto">El cliente puede ingresar a la sala</p>
                </div>`;
            setTimeout(() => {
                document.getElementById('resultado').style.display = 'none';
                document.getElementById('codigoQR').focus();
                mostrarStatus('Esperando código...', '#6c757d');
            }, 3000);
        } else {
            mostrarStatus('❌ Error al registrar', '#e74c3c');
            alert(data.error);
        }
    } catch (e) {
        mostrarStatus('Error de conexión', '#e74c3c');
    }
}

function iniciarEscaneo() {
    document.getElementById('videoContainer').style.display = 'block';
    html5QrCode = new Html5Qrcode("video");
    html5QrCode.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: 250 },
        (decoded) => {
            document.getElementById('codigoQR').value = decoded;
            detenerEscaneo();
            verificarCodigo();
        },
        () => {}
    ).catch(() => {
        alert('No se pudo acceder a la cámara');
        document.getElementById('videoContainer').style.display = 'none';
    });
}

function detenerEscaneo() {
    if (html5QrCode) {
        html5QrCode.stop().then(() => {
            document.getElementById('videoContainer').style.display = 'none';
        });
    }
}

function mostrarStatus(msg, color) {
    const el = document.getElementById('statusIndicator');
    el.style.background = color;
    el.textContent = msg;
}

function agregarHistorial(codigo, reserva, valido, error = null) {
    const h = document.getElementById('historial');
    if (historialItems.length === 0) h.innerHTML = '';

    historialItems.unshift({ codigo, reserva, valido, error, hora: new Date() });

    const item = document.createElement('div');
    item.className = 'panelqr-hist-item ' + (valido ? 'panelqr-hist-item--valido' : 'panelqr-hist-item--invalido');
    item.innerHTML = `
        <div>
            <div class="panelqr-hist-estado ${valido ? 'panelqr-hist-estado--valido' : 'panelqr-hist-estado--invalido'}">
                ${valido ? '✅ VÁLIDO' : '❌ INVÁLIDO'}
            </div>
            <div class="panelqr-hist-codigo">${codigo}</div>
            ${reserva ? `<div class="panelqr-hist-detalle">
                ${reserva.pelicula} — ${reserva.sala}</div>` : ''}
            ${error ? `<div class="panelqr-hist-error">${error}</div>` : ''}
        </div>
        <div class="panelqr-hist-hora">
            ${new Date().toLocaleTimeString('es-AR', {hour:'2-digit', minute:'2-digit'})}
        </div>`;
    h.insertAdjacentElement('afterbegin', item);
}

function limpiarHistorial() {
    historialItems = [];
    document.getElementById('historial').innerHTML = `
        <div class="panelqr-historial-vacio-inicial">
            No hay escaneos en esta sesión
        </div>`;
}

document.getElementById('codigoQR').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') verificarCodigo();
});
