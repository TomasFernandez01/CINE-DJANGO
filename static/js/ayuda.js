// MEJORAS/REDISEÑO GEMINI: Lógica del acordeón para la página de Ayuda / FAQ
document.addEventListener('DOMContentLoaded', function () {
    const faqPreguntas = document.querySelectorAll('.faq-pregunta');
    
    faqPreguntas.forEach(function (pregunta) {
        pregunta.addEventListener('click', function () {
            const item = this.parentElement;
            
            // Cerrar otros abiertos si se desea (opcional)
            document.querySelectorAll('.faq-item').forEach(function (otroItem) {
                if (otroItem !== item) {
                    otroItem.classList.remove('abierto');
                }
            });
            
            // Alternar estado actual
            item.classList.toggle('abierto');
        });
    });
});
