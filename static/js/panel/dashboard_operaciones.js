// modificado (T14 - reorg Dashboard): renombrado desde dashboard.js. Se le
// sacó todo lo de "comboChart" (Consumo por categoría, ahora vive en
// Dashboard > Promociones como render estático) y de "tablaTopPeliculas"
// (Top 5 películas, ahora vive en Dashboard > Catálogo, también estático)
// — ninguno de los dos elementos existe ya en esta página, así que ese
// código quedaba muerto. El resto (KPIs, gráfico de ventas/entradas,
// embudo) es exactamente el mismo comportamiento de antes, sin cambios de
// lógica, solo de archivo/nombre.
(function () {
    const $ = (id) => document.getElementById(id);

    const filtroDesde = $('filtroDesde');
    const filtroHasta = $('filtroHasta');
    const filtroAgrupacion = $('filtroAgrupacion');
    const btnAplicar = $('btnAplicarFiltro');
    const divError = $('filtroError');
    const presetBtns = document.querySelectorAll('.preset-btn');
    const metricaBtns = document.querySelectorAll('#metricaToggle button');

    let ventasChart = null;
    let metricaActual = 'recaudacion';

    // ------------------------------------------------------------
    // Formateo (sin separador de miles, para que coincida con
    // |floatformat:0 del primer render hecho por Django)
    // ------------------------------------------------------------
    function formatoMoneda(valor) {
        return '$' + Math.round(valor);
    }

    function mostrarError(mensaje) {
        if (!mensaje) {
            divError.style.display = 'none';
            divError.textContent = '';
            return;
        }
        divError.textContent = mensaje;
        divError.style.display = 'block';
    }

    // ------------------------------------------------------------
    // Gráfico de ventas / entradas
    // ------------------------------------------------------------
    function crearGraficoVentas(labels, valores, metrica) {
        const ctx = $('ventasChart').getContext('2d');
        const esRecaudacion = metrica === 'recaudacion';

        if (ventasChart) ventasChart.destroy();
        ventasChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: esRecaudacion ? 'Recaudación ($)' : 'Entradas vendidas',
                    data: valores,
                    borderColor: '#1a1a2e',
                    backgroundColor: 'rgba(226,185,111,0.15)',
                    fill: true,
                    tension: 0.3,
                    pointBackgroundColor: '#e2b96f',
                    pointRadius: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return esRecaudacion ? formatoMoneda(ctx.parsed.y) : ctx.parsed.y + ' entradas';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (v) { return esRecaudacion ? formatoMoneda(v) : v; }
                        }
                    }
                }
            }
        });
    }

    // ------------------------------------------------------------
    // KPIs (tarjetas de arriba)
    // ------------------------------------------------------------
    function actualizarKpis(kpis) {
        $('kpiRecaudado').textContent = formatoMoneda(kpis.recaudado_periodo);
        $('kpiTicket').textContent = formatoMoneda(kpis.ticket_promedio);
        $('kpiOcupacion').textContent = kpis.ocupacion_promedio !== null ? kpis.ocupacion_promedio + '%' : '—';
        $('kpiDiaHorario').textContent = kpis.dia_top || '—';
        $('kpiHorarioSub').textContent = kpis.horario_pico ? kpis.horario_pico + ' hs' : 'sin datos';

        const comparativaEl = $('kpiComparativa');
        comparativaEl.classList.remove('subida', 'bajada');
        if (kpis.comparativa_pct !== null) {
            const signo = kpis.comparativa_pct > 0 ? '▲' : (kpis.comparativa_pct < 0 ? '▼' : '▬');
            comparativaEl.textContent = signo + ' ' + kpis.comparativa_pct + '% vs. período anterior';
            if (kpis.comparativa_pct > 0) comparativaEl.classList.add('subida');
            if (kpis.comparativa_pct < 0) comparativaEl.classList.add('bajada');
        } else {
            comparativaEl.textContent = 'Sin datos del período anterior para comparar';
        }

        // Embudo de reservas
        const embudo = kpis.embudo || {};
        document.querySelectorAll('#embudoLista .embudo-fila .cantidad').forEach(function (el) {
            const estado = el.dataset.estado;
            el.textContent = embudo[estado] || 0;
        });
    }

    // ------------------------------------------------------------
    // Fetch + orquestación
    // ------------------------------------------------------------
    function actualizarTodo() {
        const desde = filtroDesde.value;
        const hasta = filtroHasta.value;
        const agrupacion = filtroAgrupacion.value;

        if (!desde || !hasta) {
            mostrarError('Elegí ambas fechas.');
            return;
        }
        if (desde > hasta) {
            mostrarError("La fecha 'desde' no puede ser posterior a 'hasta'.");
            return;
        }
        mostrarError(null);

        const qs = `?desde=${desde}&hasta=${hasta}`;
        const qsVentas = `${qs}&agrupacion=${agrupacion}&metrica=${metricaActual}`;

        fetch(window.DASHBOARD_URLS.grafico_ventas + qsVentas)
            .then(r => r.json())
            .then(data => {
                if (data.error) { mostrarError(data.error); return; }
                crearGraficoVentas(data.labels, data.valores, data.metrica);
            })
            .catch(() => mostrarError('No se pudo cargar el gráfico de ventas.'));

        fetch(window.DASHBOARD_URLS.kpis + qs)
            .then(r => r.json())
            .then(data => {
                if (data.error) { mostrarError(data.error); return; }
                actualizarKpis(data);
            })
            .catch(() => mostrarError('No se pudieron cargar los KPIs.'));
    }

    // ------------------------------------------------------------
    // Presets de rango rápido
    // ------------------------------------------------------------
    function aplicarPreset(preset) {
        const hoy = new Date();
        const hastaStr = hoy.toISOString().slice(0, 10);
        let desde = new Date(hoy);

        if (preset === '7d') {
            desde.setDate(desde.getDate() - 6);
        } else if (preset === '30d') {
            desde.setDate(desde.getDate() - 29);
        } else if (preset === 'mes') {
            desde = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
        } else if (preset === 'anio') {
            desde = new Date(hoy.getFullYear(), 0, 1);
        }

        filtroDesde.value = desde.toISOString().slice(0, 10);
        filtroHasta.value = hastaStr;

        presetBtns.forEach(b => b.classList.toggle('activo', b.dataset.preset === preset));
    }

    // ------------------------------------------------------------
    // Listeners
    // ------------------------------------------------------------
    btnAplicar.addEventListener('click', actualizarTodo);

    presetBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            aplicarPreset(this.dataset.preset);
            actualizarTodo();
        });
    });

    metricaBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            metricaActual = this.dataset.metrica;
            metricaBtns.forEach(b => b.classList.remove('activo'));
            this.classList.add('activo');
            actualizarTodo();
        });
    });

    // Render inicial (datos ya vinieron server-side, así que solo se
    // instancia el gráfico de ventas con lo que mandó Django — no hace
    // falta un fetch extra al cargar la página).
    crearGraficoVentas(
        window.DASHBOARD_INICIAL.ventasLabels,
        window.DASHBOARD_INICIAL.ventasValores,
        metricaActual
    );
})();
