// modificado: JS compartido, extraido de 4 templates que tenian practicamente el mismo
// codigo pegado inline (login.html, registro.html, cambiar_password.html y perfil.html
// -pestaña Seguridad-). Funciona para cualquiera de los 3 nombres de clase que se usaban
// para el boton (".ojo-toggle" en login, ".toggle-registro-password" en registro,
// ".toggle-password-campo" en cambiar_password y perfil), no fue necesario tocar el HTML.
document.addEventListener('DOMContentLoaded', function () {
    const toggles = document.querySelectorAll(
        '.ojo-toggle, .toggle-registro-password, .toggle-password-campo'
    );

    toggles.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const container = btn.closest('.contraseña-contenedor');
            if (!container) return;

            const input = container.querySelector('input');
            const openEye = container.querySelector('.ojo-abierto, #ojo-abierto');
            const closedEye = container.querySelector('.ojo-cerrado, #ojo-cerrado');
            if (!input || !openEye || !closedEye) return;

            if (input.type === 'password') {
                input.type = 'text';
                openEye.style.display = 'none';
                closedEye.style.display = 'block';
            } else {
                input.type = 'password';
                openEye.style.display = 'block';
                closedEye.style.display = 'none';
            }
        });
    });
});
