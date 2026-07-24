(function () {
    const checks = document.querySelectorAll('.chk-funcion');
    const chkTodas = document.getElementById('chkTodasFunciones');
    const btn = document.getElementById('btnEliminarSeleccionadas');
    if (!btn) return;

    function actualizarBoton() {
        const hayAlguno = Array.from(checks).some(c => c.checked);
        btn.disabled = !hayAlguno;
        btn.style.opacity = hayAlguno ? '1' : '0.5';
        btn.style.cursor = hayAlguno ? 'pointer' : 'not-allowed';
    }

    checks.forEach(c => c.addEventListener('change', actualizarBoton));
    chkTodas?.addEventListener('change', function () {
        checks.forEach(c => c.checked = chkTodas.checked);
        actualizarBoton();
    });
    actualizarBoton();

    // MODIFICACION GEMINI: Buscador reactivo de funciones (Estilo Netflix)
    const buscador = document.getElementById('buscadorFunciones');
    const tabla = document.querySelector('.tabla');
    const contador = document.getElementById('contadorFunciones');

    if (buscador && tabla && contador) {
        const filas = tabla.querySelectorAll('tbody tr');
        
        buscador.addEventListener('input', function () {
            const query = buscador.value.toLowerCase().trim();
            let visibles = 0;

            filas.forEach(fila => {
                // Columnas: 1 es checkbox, 2 es pelicula, 3 es sala, 4 es fecha/hora
                const celdas = fila.querySelectorAll('td');
                if (celdas.length < 4) return;

                const pelicula = celdas[1].textContent.toLowerCase();
                const sala = celdas[2].textContent.toLowerCase();
                const fecha = celdas[3].textContent.toLowerCase();

                if (pelicula.includes(query) || sala.includes(query) || fecha.includes(query)) {
                    fila.style.display = '';
                    visibles++;
                } else {
                    fila.style.display = 'none';
                }
            });

            contador.textContent = visibles;
        });
    }
})();
