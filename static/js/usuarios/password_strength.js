// modificado: JS compartido, extraido de cambiar_password.html y perfil.html (pestaña
// Seguridad), que tenian este mismo medidor de fuerza de contraseña pegado inline y
// exactamente igual en los 2 templates.
document.addEventListener('DOMContentLoaded', function () {
    const newPwdInput = document.getElementById('id_new_password1');
    const strengthBar = document.getElementById('strength-bar');
    const strengthText = document.getElementById('strength-text');

    if (!newPwdInput || !strengthBar || !strengthText) return;

    newPwdInput.addEventListener('input', function () {
        const val = newPwdInput.value;
        let score = 0;

        if (!val) {
            strengthBar.style.width = '0%';
            strengthText.textContent = 'Escribe una contraseña';
            return;
        }

        if (val.length >= 8) score++;
        if (/[A-Z]/.test(val)) score++;
        if (/[a-z]/.test(val)) score++;
        if (/[0-9]/.test(val)) score++;
        if (/[^A-Za-z0-9]/.test(val)) score++;

        const percent = (score / 5) * 100;
        strengthBar.style.width = `${percent}%`;

        if (score <= 2) {
            strengthBar.style.backgroundColor = '#ff6b6b';
            strengthText.textContent = 'Fuerza: Débil';
            strengthText.style.color = '#ff6b6b';
        } else if (score <= 4) {
            strengthBar.style.backgroundColor = '#ffc107';
            strengthText.textContent = 'Fuerza: Media';
            strengthText.style.color = '#ffc107';
        } else {
            strengthBar.style.backgroundColor = '#28a745';
            strengthText.textContent = 'Fuerza: Fuerte';
            strengthText.style.color = '#28a745';
        }
    });
});
