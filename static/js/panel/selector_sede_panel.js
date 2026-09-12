// nuevo (Sedes - Fase 3): autosubmit del selector de sede activa del Panel
(function () {
    const select = document.getElementById('panelSelectorSede');
    const form = document.getElementById('formPanelSelectorSede');
    if (!select || !form) return;

    select.addEventListener('change', function () {
        form.submit();
    });
})();
