// nuevo (Sedes - Fase 2): el selector "Elegí tu cine" de la navbar
// (ver templates/base.html, #selectorSede) envía el form automáticamente
// al cambiar de opción, sin necesitar un botón "Aplicar" aparte.
(function () {
    const select = document.getElementById('selectorSede');
    const form = document.getElementById('formSelectorSede');
    if (!select || !form) return;

    select.addEventListener('change', function () {
        form.submit();
    });
})();
