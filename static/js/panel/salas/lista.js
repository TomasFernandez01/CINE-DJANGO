(function () {
    const checks = document.querySelectorAll('.chk-sala');
    const btn = document.getElementById('btnEliminarSeleccionadas');

    function actualizarBoton() {
        const hayAlguno = Array.from(checks).some(c => c.checked);
        btn.disabled = !hayAlguno;
        btn.style.opacity = hayAlguno ? '1' : '0.5';
        btn.style.cursor = hayAlguno ? 'pointer' : 'not-allowed';
    }

    checks.forEach(c => c.addEventListener('change', actualizarBoton));
    actualizarBoton();
})();
