// nuevo: dashboard interactivo del Panel.
//
// Maneja:
//   1. El filtro de fechas + agrupación (día/semana/mes/bimestre/trimestre/
//      cuatrimestre/anual) y los 4 presets rápidos.
//   2. El toggle Recaudación($) / Entradas vendidas del gráfico de ventas.
//   3. Los 3 fetch() a panel/views/dashboard.py (grafico_ventas,
//      grafico_combos, kpis) que redibujan todo sin recargar la página.
//
// window.DASHBOARD_INICIAL y window.DASHBOARD_URLS vienen inyectados desde
// panel/templates/panel/inicio.html (ver <script> arriba de este archivo).

(function () {
    const $ = (id) => document.getElementById(id);

    const inputDesde = $('filtroDesde');
    const inputHasta = $('filtroHasta');
    const selectAgrupacion = $('filtroAgrupacion');
    const btnAplicar = $('btnAplicarFiltro');
    const divError = $('filtroError');
    const presetBtns = document.querySelectorAll('.preset-btn');
    const metricaBtns = document.querySelectorAll('#metricaToggle button');

    let metricaActual = 'recaudacion';
    let ventasChart = null;
    let comboChart = null;

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
    // Gráficos (Chart.js)
    // ------------------------------------------------------------
    function crearGraficoVentas(labels, valores, metrica) {
        const ctx = $('ventasChart').getContext('2d');
        const gradiente = ctx.createLinearGradient(0, 0, 0, 240);
        gradiente.addColorStop(0, 'rgba(52, 152, 219, 0.4)');
        gradiente.addColorStop(1, 'rgba(52, 152, 219, 0.0)');

        if (ventasChart) ventasChart.destroy();
        ventasChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: metrica === 'entradas' ? 'Entradas vendidas' : 'Ventas ($)',
                    data: valores,
                    borderColor: '#3498db',
                    borderWidth: 3,
                    backgroundColor: gradiente,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#3498db',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#f0f2f5' },
                        ticks: { color: '#888', font: { size: 10 } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#888', font: { size: 10 } }
                    }
                }
            }
        });
    }

    function crearGraficoCombos(labels, valores) {
        const ctx = $('comboChart').getContext('2d');
        const colores = ['#e2b96f', '#f39c12', '#27ae60', '#2ecc71', '#9b59b6', '#34495e'];

        if (comboChart) comboChart.destroy();
        comboChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels.length > 0 ? labels : ['Sin consumo en el período'],
                datasets: [{
                    data: valores.length > 0 ? valores : [1],
                    backgroundColor: valores.length > 0 ? colores.slice(0, labels.length) : ['#e0e0e0'],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#444', font: { size: 10 }, boxWidth: 12, padding: 8 }
                    }
                },
                cutout: '60%'
            }
        });
    }

    // ------------------------------------------------------------
    // KPIs (tarjetas + tabla de top películas + embudo)
    // ------------------------------------------------------------
    function actualizarKpis(kpis) {
        $('kpiRecaudado').textContent = formatoMoneda(kpis.recaudado_periodo);
        $('kpiTicket').textContent = formatoMoneda(kpis.ticket_promedio);

        const divComparativa = $('kpiComparativa');
        divComparativa.classList.remove('subida', 'bajada');
        if (kpis.comparativa_pct === null || kpis.comparativa_pct === undefined) {
            divComparativa.textContent = 'Sin datos del período anterior para comparar';
        } else {
            const flecha = kpis.comparativa_pct > 0 ? '▲' : (kpis.comparativa_pct < 0 ? '▼' : '▬');
            divComparativa.textContent = flecha + ' ' + kpis.comparativa_pct + '% vs. período anterior';
            if (kpis.comparativa_pct > 0) divComparativa.classList.add('subida');
            if (kpis.comparativa_pct < 0) divComparativa.classList.add('bajada');
        }

        $('kpiOcupacion').textContent = (kpis.ocupacion_promedio !== null && kpis.ocupacion_promedio !== undefined)
            ? kpis.ocupacion_promedio + '%' : '—';

        $('kpiDiaHorario').textContent = kpis.dia_top || '—';
        $('kpiHorarioSub').textContent = '🕐 ' + (kpis.horario_pico ? kpis.horario_pico + ' hs' : 'sin datos');

        // Top películas
        const tbody = document.querySelector('#tablaTopPeliculas tbody');
        tbody.innerHTML = '';
        if (!kpis.top_peliculas || kpis.top_peliculas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" style="padding:2rem;text-align:center;color:#999;">Sin ventas en este período.</td></tr>';
        } else {
            kpis.top_peliculas.forEach(function (p) {
                const tr = document.createElement('tr');
                const tdTitulo = document.createElement('td');
                tdTitulo.style.fontWeight = '600';
                tdTitulo.textContent = p.titulo || '—';
                const tdTotal = document.createElement('td');
                tdTotal.style.color = '#27ae60';
                tdTotal.style.fontWeight = '600';
                tdTotal.textContent = formatoMoneda(p.total);
                tr.appendChild(tdTitulo);
                tr.appendChild(tdTotal);
                tbody.appendChild(tr);
            });
        }

        // Embudo de reservas
        const embudo = kpis.embudo || {};
        const filas = document.querySelectorAll('#embudoLista .embudo-fila .cantidad');
        const estados = ['confirmada', 'pendiente', 'cancelada', 'expirada'];
        filas.forEach(function (celda, i) {
            celda.textContent = embudo[estados[i]] || 0;
        });
    }

    // ------------------------------------------------------------
    // Fetch + orquestación
    // ------------------------------------------------------------
    function aplicarFiltro() {
        const desde = inputDesde.value;
        const hasta = inputHasta.value;
        const agrupacion = selectAgrupacion.value;

        if (!desde || !hasta) {
            mostrarError('Elegí las dos fechas (desde y hasta).');
            return;
        }
        mostrarError(null);

        const qsVentas = `?desde=${desde}&hasta=${hasta}&agrupacion=${agrupacion}&metrica=${metricaActual}`;
        const qsCombos = `?desde=${desde}&hasta=${hasta}`;

        fetch(window.DASHBOARD_URLS.grafico_ventas + qsVentas)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) { mostrarError(data.error); return; }
                crearGraficoVentas(data.labels, data.valores, data.metrica);
            })
            .catch(function () { mostrarError('No se pudo cargar el gráfico de ventas.'); });

        fetch(window.DASHBOARD_URLS.grafico_combos + qsCombos)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) { mostrarError(data.error); return; }
                crearGraficoCombos(data.labels, data.valores);
            })
            .catch(function () { mostrarError('No se pudo cargar el gráfico de consumo.'); });

        fetch(window.DASHBOARD_URLS.kpis + qsCombos)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) { mostrarError(data.error); return; }
                actualizarKpis(data);
            })
            .catch(function () { mostrarError('No se pudieron actualizar los indicadores.'); });
    }

    function marcarPresetActivo(boton) {
        presetBtns.forEach(function (b) { b.classList.remove('activo'); });
        if (boton) boton.classList.add('activo');
    }

    function aplicarPreset(nombre, boton) {
        const hoy = new Date();
        const fmt = (d) => d.toISOString().slice(0, 10);
        let desde;
        let agrupacion = 'dia';

        if (nombre === '7d') {
            desde = new Date(hoy); desde.setDate(hoy.getDate() - 6);
        } else if (nombre === '30d') {
            desde = new Date(hoy); desde.setDate(hoy.getDate() - 29);
        } else if (nombre === 'mes') {
            desde = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
        } else if (nombre === 'anio') {
            desde = new Date(hoy.getFullYear(), 0, 1);
            agrupacion = 'mes';
        } else {
            return;
        }

        inputDesde.value = fmt(desde);
        inputHasta.value = fmt(hoy);
        selectAgrupacion.value = agrupacion;
        marcarPresetActivo(boton);
        aplicarFiltro();
    }

    // ------------------------------------------------------------
    // Eventos
    // ------------------------------------------------------------
    btnAplicar.addEventListener('click', function () {
        marcarPresetActivo(null); // filtro manual: ningún preset queda "activo"
        aplicarFiltro();
    });

    presetBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            aplicarPreset(btn.dataset.preset, btn);
        });
    });

    metricaBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            metricaActual = btn.dataset.metrica;
            metricaBtns.forEach(function (b) { b.classList.remove('activo'); });
            btn.classList.add('activo');
            aplicarFiltro();
        });
    });

    // ------------------------------------------------------------
    // Primer render: usa los datos que ya mandó el servidor (sin fetch),
    // así el dashboard no arranca vacío mientras carga todo lo demás.
    // ------------------------------------------------------------
    document.addEventListener('DOMContentLoaded', function () {
        const inicial = window.DASHBOARD_INICIAL;
        crearGraficoVentas(inicial.ventasLabels, inicial.ventasValores, 'recaudacion');
        crearGraficoCombos(inicial.comboLabels, inicial.comboValores);
    });
})();
