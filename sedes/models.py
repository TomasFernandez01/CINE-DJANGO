from django.db import models


class Sede(models.Model):
    """
    Una ubicación física del cine (tipo Cinemark). A partir de acá, Sala
    cuelga de una Sede (FK obligatoria) y la cartelera "de una sede" sale
    filtrando funciones por sala__sede — Pelicula sigue siendo compartida
    entre todas las sedes (el catálogo es el mismo, cada sede solo define
    en qué salas/horarios se proyecta).
    """
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    ciudad = models.CharField(max_length=100)
    telefono = models.CharField(max_length=30, blank=True)
    activa = models.BooleanField(
        default=True,
        help_text="Si está desactivada, no aparece como opción en el selector de sede del cliente."
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.ciudad})"

    class Meta:
        verbose_name = 'Sede'
        verbose_name_plural = 'Sedes'
        ordering = ['nombre']
