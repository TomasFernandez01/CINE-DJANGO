// Autocompletar el multiplicador sugerido al elegir el tipo de sala (el admin
// lo puede pisar después con cualquier valor, esto es solo un atajo).
// MODIFICACION GEMINI: Sugerir nombre de sala automatico segun tipo de sala
(function () {
    const tipoSelect = document.getElementById('id_tipo');
    const multInput = document.getElementById('id_multiplicador_precio');
    const nombreInput = document.getElementById('id_nombre');
    if (!tipoSelect || !multInput) return;

    const MULTIPLICADORES_SUGERIDOS = {
        '2d': '1.00',
        '3d': '1.25',
        '2d_premium': '1.25',
        '3d_premium': '1.50',
    };

    const NOMBRES_SUGERIDOS = {
        '2d': 'Sala 2D',
        '3d': 'Sala 3D',
        '2d_premium': 'Sala Premium 2D',
        '3d_premium': 'Sala Premium 3D',
    };

    function sugerirNombre() {
        if (!nombreInput) return;
        const nombreActual = nombreInput.value.trim();
        // Si esta vacio, es 'SALA' (default) o coincide con alguno de los sugeridos previos, actualizamos
        if (nombreActual === '' || nombreActual === 'SALA' || Object.values(NOMBRES_SUGERIDOS).includes(nombreActual)) {
            nombreInput.value = NOMBRES_SUGERIDOS[tipoSelect.value] || 'Sala';
        }
    }

    tipoSelect.addEventListener('change', function () {
        const sugerido = MULTIPLICADORES_SUGERIDOS[tipoSelect.value];
        if (sugerido) multInput.value = sugerido;
        sugerirNombre();
    });

    // Ejecutar al inicio si es una sala nueva
    if (nombreInput && (nombreInput.value.trim() === '' || nombreInput.value.trim() === 'SALA')) {
        sugerirNombre();
    }
})();

(function () {
    const filasInput = document.getElementById('id_filas');
    const colsInput  = document.getElementById('id_columnas');
    const capEl      = document.getElementById('capacidadCalc');
    const filasEl    = document.getElementById('filasVal');
    const colsEl     = document.getElementById('colsVal');
    const seccionesBody = document.getElementById('seccionesBody');
    const totalFormsInput = document.querySelector('input[name$="-TOTAL_FORMS"]');
    const plantilla = document.getElementById('filaSeccionPlantilla');
    const btnAgregar = document.getElementById('btnAgregarSeccion');

    function calcularCapacidad() {
        const filasLienzo = parseInt(filasInput.value) || 0;
        const colsLienzo  = parseInt(colsInput.value) || 0;
        filasEl.textContent = filasLienzo || '?';
        colsEl.textContent  = colsLienzo || '?';

        let total = 0;
        let hayValida = false;

        seccionesBody.querySelectorAll('.fila-seccion').forEach(function (fila) {
            if (fila.style.display === 'none') return; // fue quitada por el usuario

            const deleteChk = fila.querySelector('input[type="checkbox"]');
            if (deleteChk && deleteChk.checked) return; // marcada para eliminar

            const nums = fila.querySelectorAll('input[type="number"]');
            if (nums.length < 4) return;
            const valores = Array.from(nums).map(n => parseInt(n.value));
            if (valores.some(v => isNaN(v))) return;
            const [fi, ff, ci, cf] = valores;
            if (ff < fi || cf < ci) return;

            total += (ff - fi + 1) * (cf - ci + 1);
            hayValida = true;
        });

        // Si hay al menos una sección con datos completos, la capacidad real
        // es la suma de sus áreas (no cuenta pasillos). Si todavía no se
        // cargó ninguna sección, se muestra la grilla uniforme legacy.
        capEl.textContent = hayValida ? (total || '—') : ((filasLienzo * colsLienzo) || '—');
    }

    // "+ Agregar sección": clona la fila plantilla con un índice nuevo
    btnAgregar?.addEventListener('click', function () {
        const index = parseInt(totalFormsInput.value, 10);
        const nuevaFila = document.createElement('tr');
        nuevaFila.className = 'fila-seccion nueva-seccion';

        let html = '';
        plantilla.querySelectorAll('td').forEach(function (celda) {
            html += '<td>' + celda.innerHTML.replace(/__prefix__/g, index) + '</td>';
        });
        html += '<td style="text-align:center;">' +
                '<button type="button" class="btn btn-ghost btn-quitar-nueva" ' +
                'style="font-size:0.7rem; padding:0.25rem 0.6rem;">✕ Quitar</button>' +
                '</td>';
        nuevaFila.innerHTML = html;
        seccionesBody.appendChild(nuevaFila);

        totalFormsInput.value = index + 1;
        calcularCapacidad();
    });

    // "✕ Quitar" en una fila recién agregada (todavía no guardada en la BD):
    // se vacía y se oculta, así el formset la trata como "vacía" y la ignora
    // al guardar, sin necesidad de renumerar los índices del formset.
    seccionesBody.addEventListener('click', function (e) {
        if (!e.target.classList.contains('btn-quitar-nueva')) return;
        const fila = e.target.closest('tr');
        fila.querySelectorAll('input').forEach(function (input) {
            if (input.type === 'checkbox') input.checked = false;
            else input.value = '';
        });
        fila.style.display = 'none';
        calcularCapacidad();
    });

    filasInput?.addEventListener('input', calcularCapacidad);
    colsInput?.addEventListener('input', calcularCapacidad);
    seccionesBody.addEventListener('input', calcularCapacidad);
    seccionesBody.addEventListener('change', calcularCapacidad);

    calcularCapacidad();
})();

// const filasInput = document.getElementById('id_filas');
// const colsInput  = document.getElementById('id_columnas');
// const capEl   = document.getElementById('capacidadCalc');
// const filasEl = document.getElementById('filasVal');
// const colsEl  = document.getElementById('colsVal');

// function actualizarCapacidad() {
//     const f = parseInt(filasInput.value) || 0;
//     const c = parseInt(colsInput.value)  || 0;
//     capEl.textContent   = f * c || '—';
//     filasEl.textContent = f || '?';
//     colsEl.textContent  = c || '?';
// }

// filasInput?.addEventListener('input', actualizarCapacidad);
// colsInput?.addEventListener('input', actualizarCapacidad);
