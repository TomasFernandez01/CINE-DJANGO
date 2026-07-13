Objetivos del Sistema
cumplidos , a mejorar:
- Facilitar la visualización de películas en cartelera y sus funciones correspondientes.
- Permitir al usuario seleccionar asientos de forma interactiva mediante un mapa visual de la sala.
- Proveer un panel administrativo para gestionar todas las APPS.

Faltantes, a realizar:
- ~~Incluir un módulo de selección de combos de comida.~~ HECHO — el combo ya está conectado al flujo real de pago (`pagos/views.py` lo valida y lo suma al total al pagar). Sigue faltando el paso de "carrito" antes de pagar (ver más abajo).

- ~~Generar un ticket digital con un código QR único.~~ HECHO — `utils/qr_generator.py`, llamado desde `pagos/views.py`. Depende de tener instalado `qrcode[pil]`.

- Enviar el ticket al correo electrónico utilizando un servicio. LÓGICA HECHA, falta producción — `utils/email_utils.py` ya arma y envía el mail (HTML incluido), y está llamado desde `reservas/views.py` y `pagos/views.py`. Lo único que falta es cambiar `EMAIL_BACKEND` en `settings.py` de `console` (imprime en terminal) a `smtp` con credenciales reales. Las apps que intervienen: `utils/email_utils.py`, `reservas`, `pagos`, `configuracion/settings.py`.

Alcance del Proyecto (Todo a mejorar y pulir)
- Registro e inicio de sesión de usuarios.
- Gestión de APPs.
- Sistema de selección y bloqueo temporal de asientos. 
  Revisado en el código (`Reserva.save()` calcula `fecha_limite_pago`, `Funcion.asientos_ocupados()` cuenta reservas `pendiente` y `confirmada` como ocupadas): el mecanismo parece intacto y coherente, no se encontró una rotura obvia. PENDIENTE DE CONFIRMAR el síntoma puntual que se había reportado, para no dar por cerrado algo que quizás falla en un caso de concurrencia que no se ve solo leyendo el código.
  Nota aparte (11/07): se confirmó que el contador de "seleccionar asientos" sigue corriendo aunque el usuario cancele o se vaya para atrás sin pagar — es comportamiento normal del diseño actual (nada del lado del servidor detecta que el usuario se fue), pero se anota como mejora pendiente (bajar el tiempo, o cancelar apenas el usuario abandona) — prioridad baja, a mejorar al final.

- Carrito de compra para entradas y combos. (NO REALIZADO, sigue pendiente — hoy el combo se agrega directo en el paso de pago, no hay carrito previo)

- Generación automática de QR. HECHO (ver arriba)

- Envío de ticket digital por correo. (LÓGICA HECHA, falta config SMTP real — ver arriba)

- Panel de administración para el personal del cine. HECHO Y AMPLIADO — borrado masivo, TMDB, reorganización de sidebar, etc.

- Método de pago: se sacó la opción "Efectivo" (no existe en una compra online real). Quedan tarjeta débito/crédito y transferencia, todas simuladas.

Importancia del Proyecto.
[Análisis y definición de requerimientos funcionales; Diseño de casos de uso y modelado del sistema.; Arquitectura de software basada en capas.; Gestión de base de datos relacional.; Implementación de interfaces intuitivas y eficientes.;  Manejo de concurrencia en selección.; Uso de servicios externos simulados (como correo o QR).]
El propósito es entregar una solución funcional que represente un sistema real de la industria, integrando buenas prácticas de ingeniería de software y diseño profesional.
