// modificado (Hilo 1): extraído del <script> inline de asientos.html. Los datos que
// vienen de Django (bloqueos, categorías, ocupados, motivos, sala/función/csrf) se
// arman en el template (necesitan {% for %}/{{ }}) y se pasan acá como argumento
// de initMapaAsientos(config), en vez de tener toda la lógica JS mezclada con tags
// de Django en el archivo .html. Los estilos inline que armaban los innerHTML
// (paneles dinámicos) se pasaron a clases CSS nuevas en asientos.css.

function initMapaAsientos(config) {
    const {
        SALA_ID, FUNCION_ID, CSRF_TOKEN,
        bloqueosPorAsiento, categoriasPorAsiento, ocupadosPorReserva, motivoLabels,
    } = config;

    const botones = document.querySelectorAll('.asiento-btn');
    const panelAccion = document.getElementById('panelAccion');
    const panelAccionTitulo = document.getElementById('panelAccionTitulo');
    const panelAccionBody = document.getElementById('panelAccionBody');
    const panelVacio = document.getElementById('panelVacio');

    function pintarBoton(btn) {
        const codigo = btn.dataset.asiento;
        btn.classList.remove('libre', 'mantenimiento', 'reservado', 'vendido');
        btn.style.background = ''; // reset (las categorías usan color inline, no clase)
        if (ocupadosPorReserva.has(codigo)) {
            btn.classList.add('vendido');
            btn.title = codigo + ' — vendido/reservado';
            return;
        }
        const b = bloqueosPorAsiento[codigo];
        if (b) {
            btn.classList.add(b.motivo);
            btn.title = codigo + ' — ' + b.motivo_display + (b.nota ? ' (' + b.nota + ')' : '');
            return;
        }
        const c = categoriasPorAsiento[codigo];
        if (c) {
            btn.style.background = c.color;
            btn.title = codigo + ' — ' + c.nombre + ' (x' + c.multiplicador + ')';
            return;
        }
        btn.classList.add('libre');
        btn.title = codigo + ' — libre';
    }

    botones.forEach(pintarBoton);

    function cerrarPanel() {
        panelAccion.style.display = 'none';
        panelVacio.style.display = 'block';
    }

    function mostrarPanelLibre(codigo) {
        panelVacio.style.display = 'none';
        panelAccion.style.display = 'block';
        panelAccionTitulo.textContent = 'Asiento ' + codigo;

        let opciones = '';
        for (const [valor, etiqueta] of Object.entries(motivoLabels)) {
            opciones += `<option value="${valor}">${etiqueta}</option>`;
        }

        panelAccionBody.innerHTML = `
            <div class="panelasientos-panel-col panelasientos-panel-col--80">
                <div>
                    <label class="form-label">¿Qué querés hacer con este asiento?</label>
                    <select id="inputTipoAsignacion" class="panel-select">
                        <option value="bloqueo">🔒 Bloquear (mantenimiento/reservado)</option>
                        <option value="categoria">⭐ Asignar categoría especial (cambia el precio)</option>
                    </select>
                </div>

                <div id="subformBloqueo">
                    <label class="form-label">Motivo</label>
                    <select id="inputMotivo" class="panel-select">${opciones}</select>
                    <label class="form-label panelasientos-label-espaciada">Nota (opcional)</label>
                    <input type="text" id="inputNota" class="panel-input" maxlength="200"
                           placeholder="Ej: butaca rota">
                    <div class="panelasientos-nota-chica">
                        ${FUNCION_ID ? 'Se bloqueará solo para la función seleccionada.' : 'Se bloqueará de forma permanente en toda la sala.'}
                    </div>
                </div>

                <div id="subformCategoria" class="panelasientos-subform-oculto">
                    <label class="form-label">Nombre de la categoría</label>
                    <input type="text" id="inputCategoriaNombre" class="panel-input" maxlength="50" value="Mejorado">
                    <label class="form-label panelasientos-label-espaciada">Multiplicador de precio</label>
                    <input type="number" id="inputCategoriaMultiplicador" class="panel-input"
                           step="0.01" min="1.00" value="1.25">
                    <label class="form-label panelasientos-label-espaciada">Color en el mapa</label>
                    <input type="color" id="inputCategoriaColor" value="#f1c40f" class="panelasientos-color-input">
                    <div class="panelasientos-nota-chica">
                        Este asiento sigue siendo comprable, solo cambia el precio y el color.
                        Es siempre permanente (no depende de la función elegida arriba).
                    </div>
                </div>

                <div class="panelasientos-panel-botones">
                    <button type="button" id="btnConfirmarAsignacion" class="btn btn-success panelasientos-btn-flex1">
                        Confirmar
                    </button>
                    <button type="button" id="btnCancelarBloqueo" class="btn btn-ghost">Cancelar</button>
                </div>
                <div id="errorBloqueo" class="panelasientos-error-chica"></div>
            </div>
        `;

        document.getElementById('inputTipoAsignacion').addEventListener('change', function () {
            const esCategoria = this.value === 'categoria';
            document.getElementById('subformBloqueo').style.display   = esCategoria ? 'none' : 'block';
            document.getElementById('subformCategoria').style.display = esCategoria ? 'block' : 'none';
        });

        document.getElementById('btnCancelarBloqueo').onclick = cerrarPanel;
        document.getElementById('btnConfirmarAsignacion').onclick = function () {
            const tipo = document.getElementById('inputTipoAsignacion').value;
            if (tipo === 'bloqueo') {
                const motivo = document.getElementById('inputMotivo').value;
                const nota = document.getElementById('inputNota').value;
                bloquearAsiento(codigo, motivo, nota);
            } else {
                const nombre = document.getElementById('inputCategoriaNombre').value;
                const multiplicador = document.getElementById('inputCategoriaMultiplicador').value;
                const color = document.getElementById('inputCategoriaColor').value;
                asignarCategoria(codigo, nombre, multiplicador, color);
            }
        };
    }

    function mostrarPanelBloqueado(codigo) {
        const b = bloqueosPorAsiento[codigo];
        panelVacio.style.display = 'none';
        panelAccion.style.display = 'block';
        panelAccionTitulo.textContent = 'Asiento ' + codigo;

        panelAccionBody.innerHTML = `
            <div class="panelasientos-panel-col panelasientos-panel-col--60">
                <div><strong>Motivo:</strong> ${b.motivo_display}</div>
                <div><strong>Alcance:</strong> ${b.permanente ? 'Permanente (toda la sala)' : 'Solo esta función'}</div>
                ${b.nota ? `<div><strong>Nota:</strong> ${b.nota}</div>` : ''}
                <div class="panelasientos-panel-botones">
                    <button type="button" id="btnConfirmarDesbloqueo" class="btn btn-danger panelasientos-btn-flex1">
                        🔓 Desbloquear
                    </button>
                    <button type="button" id="btnCancelarDesbloqueo" class="btn btn-ghost">Cerrar</button>
                </div>
            </div>
        `;

        document.getElementById('btnCancelarDesbloqueo').onclick = cerrarPanel;
        document.getElementById('btnConfirmarDesbloqueo').onclick = function () {
            desbloquearAsiento(codigo, b.bloqueo_id);
        };
    }

    function mostrarPanelCategoria(codigo) {
        const c = categoriasPorAsiento[codigo];
        panelVacio.style.display = 'none';
        panelAccion.style.display = 'block';
        panelAccionTitulo.textContent = 'Asiento ' + codigo;

        panelAccionBody.innerHTML = `
            <div class="panelasientos-panel-col panelasientos-panel-col--60">
                <div><strong>Categoría:</strong> ${c.nombre}</div>
                <div><strong>Multiplicador:</strong> x${c.multiplicador}</div>
                <div><strong>Color:</strong>
                    <span class="panelasientos-color-preview" style="background:${c.color};"></span>
                </div>
                <div class="panelasientos-nota-chica">
                    Este asiento sigue siendo comprable, solo cambia el precio y el color.
                </div>
                <div class="panelasientos-panel-botones">
                    <button type="button" id="btnConfirmarQuitarCategoria" class="btn btn-danger panelasientos-btn-flex1">
                        ⭐ Quitar categoría
                    </button>
                    <button type="button" id="btnCancelarCategoria" class="btn btn-ghost">Cerrar</button>
                </div>
            </div>
        `;

        document.getElementById('btnCancelarCategoria').onclick = cerrarPanel;
        document.getElementById('btnConfirmarQuitarCategoria').onclick = function () {
            quitarCategoria(codigo, c.categoria_id);
        };
    }

    // MODIFICACION GEMINI: Seleccion multiple de asientos (por Ctrl/Cmd o boton)
    const asientosSeleccionados = new Set();
    let modoSeleccionMultiple = false;
    const btnModoSeleccion = document.getElementById('btnModoSeleccion');

    if (btnModoSeleccion) {
        btnModoSeleccion.addEventListener('click', function () {
            modoSeleccionMultiple = !modoSeleccionMultiple;
            this.classList.toggle('activo', modoSeleccionMultiple);
            if (!modoSeleccionMultiple) {
                // Limpiar seleccion si se desactiva
                limpiarSeleccionMultiple();
            }
        });
    }

    function limpiarSeleccionMultiple() {
        asientosSeleccionados.clear();
        botones.forEach(btn => btn.classList.remove('seleccionado'));
        cerrarPanel();
    }

    botones.forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            const codigo = this.dataset.asiento;
            if (ocupadosPorReserva.has(codigo)) return; // vendido, no clicable

            // Activar seleccion multiple si el boton esta activo o se presiona Ctrl/Cmd
            const usarSeleccionMultiple = modoSeleccionMultiple || e.ctrlKey || e.metaKey;

            if (usarSeleccionMultiple) {
                // Solo permitimos seleccion masiva de asientos que no esten ya reservados/vendidos
                if (asientosSeleccionados.has(codigo)) {
                    asientosSeleccionados.delete(codigo);
                    this.classList.remove('seleccionado');
                } else {
                    asientosSeleccionados.add(codigo);
                    this.classList.add('seleccionado');
                }

                if (asientosSeleccionados.size === 0) {
                    cerrarPanel();
                } else {
                    // Mostrar panel de accion para multiples asientos
                    const codigosArray = Array.from(asientosSeleccionados);
                    const codigosStr = codigosArray.join(',');

                    // Decidir si los asientos son mayormente libres o bloqueados para sugerir accion
                    const algunoBloqueado = codigosArray.some(c => bloqueosPorAsiento[c]);

                    if (algunoBloqueado && codigosArray.every(c => bloqueosPorAsiento[c])) {
                        // Si todos estan bloqueados, permitir desbloqueo masivo
                        mostrarPanelBloqueadoMasivo(codigosArray);
                    } else {
                        // En cualquier otro caso, asumimos que quieren bloquear o categorizar en lote
                        mostrarPanelLibre(codigosStr);
                    }
                }
            } else {
                // Clic simple normal: limpiar seleccion masiva previa primero
                limpiarSeleccionMultiple();

                if (bloqueosPorAsiento[codigo]) {
                    mostrarPanelBloqueado(codigo);
                } else if (categoriasPorAsiento[codigo]) {
                    mostrarPanelCategoria(codigo);
                } else {
                    mostrarPanelLibre(codigo);
                }
            }
        });
    });

    // Panel especial para desbloquear multiples asientos en lote
    function mostrarPanelBloqueadoMasivo(codigosArray) {
        panelVacio.style.display = 'none';
        panelAccion.style.display = 'block';
        panelAccionTitulo.textContent = 'Asientos Seleccionados';

        panelAccionBody.innerHTML = `
            <div class="panelasientos-panel-col panelasientos-panel-col--60">
                <div><strong>Asientos:</strong> ${codigosArray.join(', ')}</div>
                <div class="panelasientos-texto-alerta">Todos los asientos seleccionados estan bloqueados.</div>
                <div class="panelasientos-panel-botones">
                    <button type="button" id="btnConfirmarDesbloqueoMasivo" class="btn btn-danger panelasientos-btn-flex1">
                        🔓 Desbloquear todos
                    </button>
                    <button type="button" id="btnCancelarDesbloqueoMasivo" class="btn btn-ghost">Cerrar</button>
                </div>
            </div>
        `;

        document.getElementById('btnCancelarDesbloqueoMasivo').onclick = cerrarPanel;
        document.getElementById('btnConfirmarDesbloqueoMasivo').onclick = function () {
            if (!confirm('¿Desbloquear los asientos seleccionados?')) return;

            // Desbloquear uno por uno
            let promesas = [];
            codigosArray.forEach(codigo => {
                const b = bloqueosPorAsiento[codigo];
                if (b) {
                    const fd = new FormData();
                    fd.append('bloqueo_id', b.bloqueo_id);
                    fd.append('csrfmiddlewaretoken', CSRF_TOKEN);
                    promesas.push(
                        fetch(`/panel/salas/${SALA_ID}/asientos/desbloquear/`, { method: 'POST', body: fd })
                    );
                }
            });

            Promise.all(promesas)
                .then(() => {
                    location.reload();
                })
                .catch(() => alert('Error al procesar el desbloqueo masivo.'));
        };
    }

    function bloquearAsiento(codigo, motivo, nota) {
        const fd = new FormData();
        fd.append('asiento_codigo', codigo);
        fd.append('motivo', motivo);
        fd.append('nota', nota);
        if (FUNCION_ID) fd.append('funcion_id', FUNCION_ID);
        fd.append('csrfmiddlewaretoken', CSRF_TOKEN);

        fetch(`/panel/salas/${SALA_ID}/asientos/bloquear/`, { method: 'POST', body: fd })
            .then(r => r.json())
            .then(data => {
                if (!data.success) {
                    const errBox = document.getElementById('errorBloqueo');
                    if (errBox) {
                        errBox.style.display = 'block';
                        errBox.textContent = Object.values(data.errors).flat().join(' ');
                    }
                    return;
                }
                cerrarPanel();
                location.reload(); // refresca también la tabla de bloqueos de abajo
            })
            .catch(() => alert('Error de conexión al bloquear los asientos.'));
    }

    function desbloquearAsiento(codigo, bloqueoId) {
        if (!confirm('¿Desbloquear el asiento ' + codigo + '?')) return;

        const fd = new FormData();
        fd.append('bloqueo_id', bloqueoId);
        fd.append('csrfmiddlewaretoken', CSRF_TOKEN);

        fetch(`/panel/salas/${SALA_ID}/asientos/desbloquear/`, { method: 'POST', body: fd })
            .then(r => r.json())
            .then(data => {
                if (!data.success) { alert('No se pudo desbloquear.'); return; }
                delete bloqueosPorAsiento[codigo];
                const btn = document.querySelector(`.asiento-btn[data-asiento="${codigo}"]`);
                if (btn) pintarBoton(btn);
                cerrarPanel();
                location.reload();
            })
            .catch(() => alert('Error de conexión al desbloquear el asiento.'));
    }

    function asignarCategoria(codigo, nombre, multiplicador, color) {
        const fd = new FormData();
        fd.append('asiento_codigo', codigo);
        fd.append('nombre', nombre);
        fd.append('multiplicador', multiplicador);
        fd.append('color', color);
        fd.append('csrfmiddlewaretoken', CSRF_TOKEN);

        fetch(`/panel/salas/${SALA_ID}/asientos/categoria/asignar/`, { method: 'POST', body: fd })
            .then(r => r.json())
            .then(data => {
                if (!data.success) {
                    const errBox = document.getElementById('errorBloqueo');
                    if (errBox) {
                        errBox.style.display = 'block';
                        errBox.textContent = Object.values(data.errors).flat().join(' ');
                    }
                    return;
                }
                cerrarPanel();
                location.reload(); // refresca también la tabla de categorías de abajo
            })
            .catch(() => alert('Error de conexión al asignar la categoría.'));
    }

    function quitarCategoria(codigo, categoriaId) {
        if (!confirm('¿Quitar la categoría especial del asiento ' + codigo + '?')) return;

        const fd = new FormData();
        fd.append('categoria_id', categoriaId);
        fd.append('csrfmiddlewaretoken', CSRF_TOKEN);

        fetch(`/panel/salas/${SALA_ID}/asientos/categoria/quitar/`, { method: 'POST', body: fd })
            .then(r => r.json())
            .then(data => {
                if (!data.success) { alert('No se pudo quitar la categoría.'); return; }
                delete categoriasPorAsiento[codigo];
                const btn = document.querySelector(`.asiento-btn[data-asiento="${codigo}"]`);
                if (btn) pintarBoton(btn);
                cerrarPanel();
                location.reload();
            })
            .catch(() => alert('Error de conexión al quitar la categoría.'));
    }

    // Botones "Quitar" en la tabla inferior
    document.querySelectorAll('.btn-desbloquear-fila').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const fila = this.closest('tr');
            desbloquearAsiento(fila.dataset.asiento, this.dataset.bloqueoId);
        });
    });

    // Botones "Quitar" en la tabla de categorías
    document.querySelectorAll('.btn-quitar-categoria-fila').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const fila = this.closest('tr');
            quitarCategoria(fila.dataset.asiento, this.dataset.categoriaId);
        });
    });

    // Cambio de modo (permanente <-> función)
    document.getElementById('selectorModo').addEventListener('change', function () {
        const valor = this.value;
        const url = new URL(window.location.href);
        if (valor) {
            url.searchParams.set('funcion', valor);
        } else {
            url.searchParams.delete('funcion');
        }
        window.location.href = url.toString();
    });
}
