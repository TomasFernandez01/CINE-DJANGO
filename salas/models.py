from django.db import models
from peliculas.models import Pelicula
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

class Sala(models.Model):
    nombre = models.CharField(max_length=100)
    capacidad = models.IntegerField()
    activa = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.nombre} (Cap: {self.capacidad})"
    
    class Meta:
        verbose_name = 'Sala'
        verbose_name_plural = 'Salas'
        ordering = ['nombre']


class Funcion(models.Model):
    pelicula = models.ForeignKey(Pelicula, on_delete=models.CASCADE, related_name='funciones')
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='funciones')
    fecha_hora = models.DateTimeField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.pelicula.titulo} - {self.sala.nombre} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"
    
    def asientos_disponibles(self):
        try:
            reservados = self.reservas.filter(estado__in=['pendiente', 'confirmada']).aggregate(
                total=models.Sum('cantidad_entradas')
            )['total'] or 0
            return self.sala.capacidad - reservados
        except AttributeError:
            return self.sala.capacidad

    def esta_disponible(self):
        """Verifica si la función está disponible (no pasó y está marcada como disponible)"""
        return self.disponible and self.fecha_hora > timezone.now()
    
    def puede_cancelarse(self):
        """Verifica si falta al menos 2 horas para la función"""
        return self.fecha_hora - timezone.now() > timedelta(hours=2)
    
    def tiempo_restante(self):
        """Retorna el tiempo restante hasta la función"""
        if self.fecha_hora > timezone.now():
            delta = self.fecha_hora - timezone.now()
            horas = delta.total_seconds() / 3600
            if horas < 1:
                minutos = int(delta.total_seconds() / 60)
                return f"{minutos} minutos"
            elif horas < 24:
                return f"{int(horas)} horas"
            else:
                dias = int(horas / 24)
                return f"{dias} días"
        return "Función pasada"
    
    # ============================================
    # NUEVO: VALIDACIÓN DE FUNCIONES DUPLICADAS
    # ============================================
    
    def calcular_hora_fin(self):
        """
        Calcula la hora de fin de la función.
        Duración de película + 30 minutos de margen (limpieza/publicidad)
        """
        if not self.pelicula.duracion:
            # Si no hay duración, asumir 2 horas por defecto
            duracion_total = 120 + 30  # 2h película + 30min margen
        else:
            duracion_total = self.pelicula.duracion + 30
        
        return self.fecha_hora + timedelta(minutes=duracion_total)
    
    def hay_solapamiento(self):
        """
        Verifica si esta función se solapa con otra en la misma sala.
        Retorna (bool, lista_de_funciones_solapadas)
        """
        hora_inicio = self.fecha_hora
        hora_fin = self.calcular_hora_fin()
        
        # Buscar otras funciones en la misma sala (excluyendo esta misma si ya existe)
        funciones_sala = Funcion.objects.filter(sala=self.sala)
        
        if self.pk:  # Si ya existe, excluirse a sí misma
            funciones_sala = funciones_sala.exclude(pk=self.pk)
        
        funciones_solapadas = []
        
        for otra_funcion in funciones_sala:
            otra_inicio = otra_funcion.fecha_hora
            otra_fin = otra_funcion.calcular_hora_fin()
            
            # Verificar solapamiento
            # Hay solapamiento si:
            # - Esta función empieza durante otra función
            # - Esta función termina durante otra función
            # - Esta función contiene completamente a otra función
            if (
                (hora_inicio < otra_fin and hora_fin > otra_inicio) or  # Solapamiento general
                (hora_inicio >= otra_inicio and hora_inicio < otra_fin) or  # Empieza durante otra
                (hora_fin > otra_inicio and hora_fin <= otra_fin) or  # Termina durante otra
                (hora_inicio <= otra_inicio and hora_fin >= otra_fin)  # Contiene a otra
            ):
                funciones_solapadas.append(otra_funcion)
        
        return len(funciones_solapadas) > 0, funciones_solapadas
    
    def clean(self):
        """
        Validación personalizada del modelo.
        Django llama a esto antes de guardar si se usa en forms/admin.
        """
        super().clean()
        
        # Validar que la fecha no sea en el pasado
        if self.fecha_hora and self.fecha_hora < timezone.now():
            raise ValidationError({
                'fecha_hora': 'No se puede crear una función en el pasado.'
            })
        
        # Validar solapamiento de funciones
        hay_solape, funciones = self.hay_solapamiento()
        if hay_solape:
            mensajes_error = []
            for f in funciones:
                mensajes_error.append(
                    f"Se solapa con: {f.pelicula.titulo} a las {f.fecha_hora.strftime('%H:%M')} "
                    f"(termina aproximadamente a las {f.calcular_hora_fin().strftime('%H:%M')})"
                )
            
            raise ValidationError({
                'fecha_hora': 'Esta función se solapa con otra(s) en la misma sala. ' + ' | '.join(mensajes_error)
            })
    
    def save(self, *args, **kwargs):
        """
        Sobrescribir save para forzar validación incluso sin forms.
        """
        # Llamar a clean() manualmente si no se está usando un form
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Función'
        verbose_name_plural = 'Funciones'
        ordering = ['fecha_hora']
        # Índice compuesto para búsquedas rápidas de solapamiento
        indexes = [
            models.Index(fields=['sala', 'fecha_hora']),
        ]