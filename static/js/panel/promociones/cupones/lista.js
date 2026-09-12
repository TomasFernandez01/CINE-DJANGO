(function () {
    const checks = document.querySelectorAll('.chk-cupon');
    const chkTodos = document.getElementById('chkTodosCupones');
    const btn = document.getElementById('btnEliminarSeleccionadas');
    if (!btn) return;

    function actualizarBoton() {
        const hayAlguno = Array.from(checks).some(c => c.checked);
        btn.disabled = !hayAlguno;
        btn.style.opacity = hayAlguno ? '1' : '0.5';
        btn.style.cursor = hayAlguno ? 'pointer' : 'not-allowed';
    }

    checks.forEach(c => c.addEventListener('change', actualizarBoton));
    chkTodos?.addEventListener('change', function () {
        checks.forEach(c => c.checked = chkTodos.checked);
        actualizarBoton();
    });
    actualizarBoton();
})();
