// modificado: extraído del <script> inline de seleccionar_asientos.html
// (~300 líneas). Los valores que antes venían directo del template
// ({{ funcion.precio_final }}, {{ max_asientos }}, {{ funcion.id }},
// segundos_restantes, {{ tiempo_limite_minutos }}, la url de "lista
// funciones" y la de "verificar asientos") ahora se leen desde
// data-attributes del contenedor #seleccionarAsientosData (ver
// seleccionar_asientos.html), en vez de estar embebidos en el JS.
(function () {
    const datos = document.getElementById('seleccionarAsientosData');
    if (!datos) return;

    // ─── Constantes desde Django ────────────────────────────────
    const PRECIO_ENTRADA  = parseFloat(datos.dataset.precioEntrada);
    const MAX_ASIENTOS    = parseInt(datos.dataset.maxAsientos, 10);
    const SEGUNDOS_RESTANTES = datos.dataset.segundosRestantes ? parseInt(datos.dataset.segundosRestantes, 10) : null;
    const TIEMPO_LIMITE_MINUTOS = datos.dataset.tiempoLimiteMinutos;
    const URL_LISTA_FUNCIONES = datos.dataset.urlListaFunciones;
    const URL_VERIFICAR_ASIENTOS = datos.dataset.urlVerificarAsientos;
    const PRECIOS_POR_ASIENTO = JSON.parse(document.getElementById('precios-por-asiento-data').textContent);
    const INFO_CATEGORIAS     = JSON.parse(document.getElementById('info-categorias-data').textContent);

    // ─── Estado ─────────────────────────────────────────────────
    const asientosSeleccionados = new Set();
    let formularioBloqueado = false;

    // ─── Referencias DOM ────────────────────────────────────────
    const botonesAsientos = document.querySelectorAll('.asiento.disponible');
    const textoAsientos   = document.getElementById('asientosSeleccionadosTexto');
    const textoCantidad   = document.getElementById('cantidadSeleccionada');
    const textoTotal      = document.getElementById('totalPagar');
    const inputOculto     = document.getElementById('asientosSeleccionadosInput');
    const btnConfirmar    = document.getElementById('btnConfirmar');
    const formReserva     = document.getElementById('formReserva');
    const banner          = document.getElementById('countdownBanner');
    const countdownEl     = document.getElementById('countdown');
    const notaCategorias  = document.getElementById('notaCategoriasSeleccionadas'); // nuevo para que muestre el tipo de sala

    // ════════════════════════════════════════════════════════════
    // COUNTDOWN
    // Blindado con "if (banner && countdownEl)": si el banner de arriba
    // está comentado en el HTML (como está ahora), banner/countdownEl son
    // null y este bloque simplemente no hace nada, en vez de tirar un
    // TypeError que frenaba TODO el script de acá para abajo (por eso no
    // andaba la selección de asientos ni el submit del formulario)
    // ════════════════════════════════════════════════════════════
    if (SEGUNDOS_RESTANTES) {
        if (banner && countdownEl) {
            let tiempoRestante = parseInt(banner.dataset.segundos, 10);

            var formatearTiempo = function (seg) {
                const m = Math.floor(seg / 60);
                const s = seg % 60;
                return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
            };

            var expirarSesion = function () {
                // Bloquear formulario
                formularioBloqueado = true;
                if (btnConfirmar) {
                    btnConfirmar.disabled = true;
                    btnConfirmar.style.opacity = '0.4';
                    btnConfirmar.style.cursor = 'not-allowed';
                    btnConfirmar.textContent = '⏰ Tiempo Expirado';
                }
                if (formReserva) {
                    formReserva.style.opacity = '0.5';
                    formReserva.style.pointerEvents = 'none';
                }
                // Bloquear asientos
                botonesAsientos.forEach(b => {
                    b.disabled = true;
                    b.style.cursor = 'not-allowed';
                });

                // Cambiar banner
                banner.style.background = 'linear-gradient(135deg, #6c757d 0%, #495057 100%)';
                banner.style.boxShadow  = 'none';
                countdownEl.textContent = '00:00';

                // Alerta y redirige
                setTimeout(function () {
                    alert('⏰ El tiempo para seleccionar asientos expiró. Serás redirigido a las funciones disponibles.');
                    window.location.href = URL_LISTA_FUNCIONES;
                }, 800);
            };

            var actualizarContadorBanner = function () {
                if (tiempoRestante <= 0) {
                    clearInterval(intervaloBanner);
                    expirarSesion();
                    return;
                }

                countdownEl.textContent = formatearTiempo(tiempoRestante);

                // Alerta visual: menos de 2 minutos → rojo intenso + pulso
                if (tiempoRestante <= 120) {
                    banner.style.background = 'linear-gradient(135deg, #dc3545 0%, #c82333 100%)';
                    countdownEl.style.animation = 'pulso 1s infinite';
                }
                // Alerta visual: menos de 1 minuto → parpadeo más rápido
                if (tiempoRestante <= 60) {
                    countdownEl.style.animation = 'pulsoRapido 0.5s infinite';
                }

                tiempoRestante--;
            };

            // Iniciar inmediatamente y luego cada segundo
            actualizarContadorBanner();
            var intervaloBanner = setInterval(actualizarContadorBanner, 1000);
        }
    }

    // ════════════════════════════════════════════════════════════
    // SELECCIÓN DE ASIENTOS
    // modificado: paleta nueva estilo Cinemark (Fase 1, solo visual)
    //   - Disponible normal   → blanco
    //   - Categoría especial  → rojo fijo (antes usaba info.color, el color
    //     propio de cada categoría cargado desde el admin; ahora se unifica
    //     en rojo para que combine con el resto de la paleta. El dato
    //     info.color de la base sigue existiendo por si en el futuro se
    //     quiere volver a usarlo por categoría)
    //   - Seleccionado        → círculo rojo con carita feliz ":)" en vez
    //     del código, sea cual sea el color que tenía antes de elegirlo
    // ════════════════════════════════════════════════════════════

    const COLOR_DISPONIBLE       = { fondo: '#ffffff', borde: '#cccccc', texto: '#111111' };
    const COLOR_CATEGORIA        = { fondo: '#f1c40f', borde: '#c29d0b', texto: '#111111' };
    const COLOR_SELECCIONADO     = { fondo: '#e63946', borde: '#b3202c', texto: '#ffffff' };

    // Guardar el estado base (blanco) de cada asiento disponible, para
    // poder restaurarlo tal cual al deseleccionar.
    botonesAsientos.forEach(function (boton) {
        boton.dataset.colorBase  = COLOR_DISPONIBLE.fondo;
        boton.dataset.borderBase = COLOR_DISPONIBLE.borde;
        boton.dataset.textoBase  = COLOR_DISPONIBLE.texto;
    });

    // Los asientos con categoría especial pisan ese estado base con rojo.
    Object.entries(INFO_CATEGORIAS).forEach(function ([codigo, info]) {
        const btn = document.querySelector('.asiento.disponible[data-asiento="' + codigo + '"]');
        if (btn) {
            btn.dataset.colorBase  = COLOR_CATEGORIA.fondo;
            btn.dataset.borderBase = COLOR_CATEGORIA.borde;
            btn.dataset.textoBase  = COLOR_CATEGORIA.texto;
            btn.title = codigo + ' — ' + info.nombre + ' (x' + info.multiplicador + ', +' + Math.round((info.multiplicador - 1) * 100) + '%)';
        }
    });

    // Pintar cada asiento disponible con su estado base recién calculado.
    botonesAsientos.forEach(function (boton) {
        boton.style.backgroundColor = boton.dataset.colorBase;
        boton.style.borderColor     = boton.dataset.borderBase;
        boton.style.color           = boton.dataset.textoBase;
    });

    botonesAsientos.forEach(function (boton) {
        // Click
        boton.addEventListener('click', function () {
            if (formularioBloqueado) return;

            const codigo = this.dataset.asiento;

            if (asientosSeleccionados.has(codigo)) {
                // Deseleccionar: vuelve a su estado base (blanco, o rojo
                // si es categoría especial) y al código como texto de nuevo.
                asientosSeleccionados.delete(codigo);
                this.style.backgroundColor = this.dataset.colorBase;
                this.style.borderColor     = this.dataset.borderBase;
                this.style.color           = this.dataset.textoBase;
                this.style.borderRadius    = '6px';
                this.textContent           = codigo;
                this.style.transform       = 'scale(1)';
            } else {
                // Validar límite
                if (asientosSeleccionados.size >= MAX_ASIENTOS) {
                    mostrarAlertaLimite();
                    return;
                }
                asientosSeleccionados.add(codigo);
                // Seleccionado: círculo rojo con carita feliz, reemplazando
                // el código (manda por sobre el color de categoría especial)
                this.style.backgroundColor = COLOR_SELECCIONADO.fondo;
                this.style.borderColor     = COLOR_SELECCIONADO.borde;
                this.style.color           = COLOR_SELECCIONADO.texto;
                this.style.borderRadius    = '50%';
                this.textContent           = ':)';
            }
            actualizarResumen();
        });

        // Hover — modificado: sombra clara en vez de oscura, para que se note sobre el fondo negro
        boton.addEventListener('mouseenter', function () {
            if (!asientosSeleccionados.has(this.dataset.asiento) && !formularioBloqueado) {
                this.style.transform = 'scale(1.12)';
                this.style.boxShadow = '0 0 8px rgba(255,255,255,0.5)';
            }
        });
        boton.addEventListener('mouseleave', function () {
            if (!asientosSeleccionados.has(this.dataset.asiento)) {
                this.style.transform = 'scale(1)';
                this.style.boxShadow = 'none';
            }
        });
    });

    function mostrarAlertaLimite() {
        // Animación breve en el botón confirmar
        if (btnConfirmar) {
            btnConfirmar.style.animation = 'sacudida 0.4s';
            setTimeout(() => { btnConfirmar.style.animation = ''; }, 400);
        }
        alert('⚠️ Solo podés seleccionar hasta ' + MAX_ASIENTOS + ' asientos por reserva.');
    }

    // ─── Actualizar resumen inferior ────────────────────────────
    function actualizarResumen() {
        const cantidad = asientosSeleccionados.size;
        //const total    = cantidad * PRECIO_ENTRADA;
        let total = 0;
        asientosSeleccionados.forEach(function (codigo) {
            total += (PRECIOS_POR_ASIENTO[codigo] !== undefined ? PRECIOS_POR_ASIENTO[codigo] : PRECIO_ENTRADA);
        });
        if (cantidad === 0) {
            textoAsientos.textContent = 'Ninguno';
            btnConfirmar.disabled     = true;
            btnConfirmar.style.cursor  = 'not-allowed';
            btnConfirmar.style.opacity = '0.5';
        } else {
            const arr = Array.from(asientosSeleccionados).sort();
            textoAsientos.textContent = arr.join(', ');
            if (!formularioBloqueado) {
                btnConfirmar.disabled     = false;
                btnConfirmar.style.cursor  = 'pointer';
                btnConfirmar.style.opacity = '1';
            }
        }

        textoCantidad.textContent = cantidad;
        textoTotal.textContent    = '$' + total.toFixed(2);
        inputOculto.value         = Array.from(asientosSeleccionados).sort().join(',');

        // Detalle de por qué el total puede ser más alto: qué asientos
        // seleccionados tienen categoría especial y cuánto multiplican.
        const detalles = [];
        asientosSeleccionados.forEach(function (codigo) {
            const info = INFO_CATEGORIAS[codigo];
            if (info) {
                detalles.push('⭐ ' + codigo + ' es "' + info.nombre + '": +' +
                              Math.round((info.multiplicador - 1) * 100) + '% sobre el precio base');
            }
        });
        notaCategorias.innerHTML = detalles.length ? detalles.join('<br>') : '';
    }

    // ════════════════════════════════════════════════════════════
    // VALIDACIÓN AL ENVIAR
    // ════════════════════════════════════════════════════════════
    formReserva.addEventListener('submit', function (e) {
        // Bloqueo por tiempo
        if (formularioBloqueado) {
            e.preventDefault();
            alert('⏰ El tiempo expiró. Por favor, volvé a las funciones y comenzá de nuevo.');
            return false;
        }

        // Sin asientos
        if (asientosSeleccionados.size === 0) {
            e.preventDefault();
            alert('⚠️ Debés seleccionar al menos un asiento antes de confirmar.');
            return false;
        }

        // Excede el límite (doble-check)
        if (asientosSeleccionados.size > MAX_ASIENTOS) {
            e.preventDefault();
            alert('⚠️ Solo podés reservar hasta ' + MAX_ASIENTOS + ' asientos.');
            return false;
        }

        // modificado: ya se mostró el modal y el usuario confirmó — dejamos
        // que este segundo submit (disparado por nosotros mismos, ver abajo)
        // siga su curso normal en vez de volver a interceptarlo.
        if (formReserva.dataset.confirmado === 'si') {
            return true;
        }

        // modificado: antes acá había un confirm() nativo del navegador (se
        // veía "roto" con el resto del estilo de la página). Ahora se
        // frena el submit, se muestra el modal compartido, y recién si el
        // usuario confirma ahí adentro se vuelve a mandar el formulario.
        e.preventDefault();

        const arr   = Array.from(asientosSeleccionados).sort();
        const total = arr.length * PRECIO_ENTRADA;

        window.mostrarModalConfirmacion({
            titulo: 'Confirmar reserva',
            mensaje: 'Asientos: ' + arr.join(', ') + '\n' +
                      'Cantidad: ' + arr.length + '\n' +
                      'Total: $' + total.toFixed(2) + '\n\n' +
                      'A partir de este momento vas a tener ' + TIEMPO_LIMITE_MINUTOS + ' minutos para completar el pago.',
            textoConfirmar: 'Confirmar reserva',
            textoCancelar: 'Seguir eligiendo',
            peligro: false
        }).then(function (confirmado) {
            if (!confirmado) return;
            formReserva.dataset.confirmado = 'si';
            if (formReserva.requestSubmit) {
                formReserva.requestSubmit();
            } else {
                formReserva.submit();
            }
        });

        return false;
    });

    // ════════════════════════════════════════════════════════════
    // VERIFICACIÓN PERIÓDICA DE DISPONIBILIDAD (cada 10 s)
    // ════════════════════════════════════════════════════════════
    setInterval(function () {
        if (formularioBloqueado) return;

        fetch(URL_VERIFICAR_ASIENTOS)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.success) return;

                const ocupadosNuevos = data.asientos_ocupados;
                let conflicto = false;

                asientosSeleccionados.forEach(function (asiento) {
                    if (ocupadosNuevos.includes(asiento)) {
                        conflicto = true;
                        asientosSeleccionados.delete(asiento);
                    }
                });

                if (conflicto) {
                    actualizarResumen();
                    alert('Algunos asientos que seleccionaste acaban de ser reservados por otro usuario. Por favor, elegí otros.');
                    location.reload();
                }
            })
            .catch(function () { /* silenciar errores de red */ });
    }, 10000);

})();
