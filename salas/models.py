from django.db import models
from peliculas.models import Pelicula
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

class Sala(models.Model):
    TIPO_CHOICES = [
        ('2d', '2D'),
        ('3d', '3D'),
        ('2d_premium', '2D Premium'),
        ('3d_premium', '3D Premium (IMAX/DBOX)'),
    ]
    TIPO_CONFIG = {
        '2d':        {'icono': '🎬', 'color': '#6c757d', 'badge': 'secondary'},
        '3d':        {'icono': '🥽', 'color': '#007bff', 'badge': 'primary'},
        '2d_premium':{'icono': '⭐', 'color': '#fd7e14', 'badge': 'warning'},
        '3d_premium':{'icono': '💎', 'color': '#6f42c1', 'badge': 'purple'},
    }
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='2d',
        help_text="Tipo de tecnología de la sala"
        )
    capacidad = models.IntegerField(
        default=0,
        editable=False,
        help_text="Se calcula automáticamente: filas*columnas"
        ) 
    activa = models.BooleanField(default=True)
    filas = models.IntegerField(
        default=6, 
        help_text="Cantidad de filas (A, B, C, ...)"
        )
    columnas = models.IntegerField(
        default=8, 
        help_text="Cantidad de columnas (1, 2, 3, ...)"
        )
    
    ###############################################################
    def __str__(self):
        return f"{self.nombre} [{self.get_tipo_display()}] (Cap: {self.capacidad})"
 
    def tipo_icono(self):
        return self.TIPO_CONFIG.get(self.tipo, {}).get('icono', '🎬')
 
    def tipo_color(self):
        return self.TIPO_CONFIG.get(self.tipo, {}).get('color', '#6c757d')
 
    def es_premium(self):
        return 'premium' in self.tipo
 
    def es_3d(self):
        return '3d' in self.tipo
    ###############################################################
    # antes---
    # def __str__(self):
    #     return f"{self.nombre} (Cap: {self.capacidad})"
    
    def layout_asientos(self):
        """Retorna el layout de asientos como lista de listas"""
        letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        layout = []
        for i in range(self.filas):
            fila = []
            for j in range(1, self.columnas + 1):
                fila.append(f"{letras[i]}{j}")
            layout.append(fila)
        return layout
    
    def total_asientos(self):
        """Calcula el total de asientos según filas x columnas"""
        return self.filas * self.columnas
    
    def save(self, *args, **kwargs):
        # Auto-ajustar capacidad si no está definida
        if not self.capacidad or self.capacidad != self.total_asientos():
            self.capacidad = self.total_asientos()
        super().save(*args, **kwargs)

    # PROBAR si no anda
    # def save(self, *args, **kwargs):
    #     # SIEMPRE auto-calcular capacidad
    #     self.capacidad = self.total_asientos()
    #     super().save(*args, **kwargs)
    
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
    
    # def __str__(self):
    #     return f"{self.pelicula.titulo} - {self.sala.nombre} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"
    def __str__(self):
        return f"{self.pelicula.titulo} - {self.sala.nombre} [{self.sala.get_tipo_display()}] - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"

    # NUEVO: ahora los metodos orbitan a a funcion asienos_ocupados
    def asientos_ocupados(self):
        """
        Retorna una lista de códigos de asientos ocupados (confirmados o pendientes).
        Ejemplo: ['A1', 'A2', 'B5', 'C3']
        """
        from reservas.models import Reserva
        reservas = self.reservas.filter(estado__in=['pendiente', 'confirmada'])
        
        asientos = []
        for reserva in reservas:
            if reserva.asientos_seleccionados:
                # asientos_seleccionados es un string: "A1,A2,B5"
                asientos.extend(reserva.asientos_seleccionados.split(','))
        
        return asientos
    # ============================================
    # NUEVO: ASIENTOS BLOQUEADOS/NO DISPONIBLES
    # ============================================
    def asientos_bloqueados(self):
        """
        Retorna una lista de códigos de asientos bloqueados por el admin
        (permanentes de la sala + específicos de esta función).
        Ejemplo: ['A1', 'C5']
        """
        bloqueos = self.sala.bloqueos_asientos.filter(
            models.Q(funcion__isnull=True) | models.Q(funcion=self)
        )
        return list(bloqueos.values_list('asiento_codigo', flat=True))

    def asientos_no_disponibles(self):
        """
        Retorna todos los códigos de asientos que NO se pueden seleccionar:
        ocupados por reserva + bloqueados por el admin (sin duplicados).
        """
        return list(set(self.asientos_ocupados()) | set(self.asientos_bloqueados()))

    def asientos_disponibles(self):
        """Retorna la cantidad de asientos disponibles"""
        no_disponibles = len(self.asientos_no_disponibles())
        return self.sala.capacidad - no_disponibles
    
    def esta_asiento_disponible(self, asiento_codigo):
        """Verifica si un asiento específico está disponible (ni ocupado ni bloqueado)"""
        return asiento_codigo not in self.asientos_no_disponibles()
    
    ###################################################
    # def asientos_disponibles(self):
    #     try:
    #         reservados = self.reservas.filter(estado__in=['pendiente', 'confirmada']).aggregate(
    #             total=models.Sum('cantidad_entradas')
    #         )['total'] or 0
    #         return self.sala.capacidad - reservados
    #     except AttributeError:
    #         return self.sala.capacidad

    def asientos_disponibles(self):
        """Retorna la cantidad de asientos disponibles"""
        ocupados = len(self.asientos_ocupados())
        return self.sala.capacidad - ocupados
    
    def esta_asiento_disponible(self, asiento_codigo):
        """Verifica si un asiento específico está disponible"""
        return asiento_codigo not in self.asientos_ocupados()
    
    ###################################################
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
        Calcula la hora de fin de la función. Duración de película + 30 minutos de margen (limpieza/publicidad)
        """
        if not self.pelicula.duracion:
            # Si no hay duración, asumir 2 horas por defecto
            duracion_total = 120 + 30  # 2h película + 30min margen
        else:
            duracion_total = self.pelicula.duracion + 30
        
        return self.fecha_hora + timedelta(minutes=duracion_total)
    
    def hay_solapamiento(self):
        """
        Verifica si esta función se solapa con otra en la misma sala. Retorna (bool, lista_de_funciones_solapadas)
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
        Validación personalizada del modelo. Django llama a esto antes de guardar si se usa en forms/admin.
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


########################################################################33
class AsientoBloqueado(models.Model):
    MOTIVO_CHOICES = [
        ('mantenimiento', 'Mantenimiento'),
        ('vip', 'VIP'),
        ('admin', 'Reservado por Admin'),
        ('reservado', 'Reservado (cortesía/especial)'),
    ]

    sala = models.ForeignKey(
        Sala,
        on_delete=models.CASCADE,
        related_name='bloqueos_asientos'
        #related_name='asientos_bloqueados',
    )
    asiento_codigo = models.CharField(
        max_length=10,
        help_text="Código del asiento, ej: A1"
    )
    motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES, default='admin')
    funcion = models.ForeignKey(
        Funcion,
        on_delete=models.CASCADE,
        #related_name='asientos_bloqueados',
        related_name='bloqueos_asientos',
        null=True,
        blank=True,
        help_text="Dejar vacío para bloqueo permanente en toda la sala. "
                   "Completar para bloquear solo en esta función."
    )
    nota = models.CharField(
        max_length=200,
        blank=True,
        help_text="Motivo puntual, opcional (ej: butaca rota, avisado 03/07)"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        alcance = f"función #{self.funcion_id}" if self.funcion_id else "permanente"
        return f"{self.sala.nombre} - {self.asiento_codigo} ({self.get_motivo_display()}, {alcance})"

    def clean(self):
        super().clean()

        # 1. Validar que el asiento_codigo exista realmente en la sala
        if self.sala_id and self.asiento_codigo:
            codigos_validos = {
                asiento
                for fila in self.sala.layout_asientos()
                for asiento in fila
            }
            if self.asiento_codigo not in codigos_validos:
                raise ValidationError({
                    'asiento_codigo': f'"{self.asiento_codigo}" no existe en la sala '
                                       f'"{self.sala.nombre}". Códigos válidos: '
                                       f'{", ".join(sorted(codigos_validos))}.'
                })

        # 2. Validar que la función (si se especifica) pertenezca a esta sala
        if self.funcion_id and self.funcion.sala_id != self.sala_id:
            raise ValidationError({
                'funcion': 'Esta función no pertenece a la sala seleccionada.'
            })

        # 3. Evitar bloqueos duplicados/ambiguos para el mismo asiento
        if self.sala_id and self.asiento_codigo:
            conflictos = AsientoBloqueado.objects.filter(
                sala_id=self.sala_id,
                asiento_codigo=self.asiento_codigo,
            )
            if self.pk:
                conflictos = conflictos.exclude(pk=self.pk)

            # Ya existe un bloqueo permanente para este asiento
            if conflictos.filter(funcion__isnull=True).exists():
                raise ValidationError(
                    f'El asiento {self.asiento_codigo} ya tiene un bloqueo permanente '
                    f'en esta sala. Elimínalo antes de crear uno nuevo.'
                )

            # Se está creando otro bloqueo permanente pero ya hay uno específico de función
            # (no es un error grave, pero avisamos para que el admin no se confunda)
            if self.funcion_id is None and conflictos.filter(funcion__isnull=False).exists():
                raise ValidationError(
                    f'El asiento {self.asiento_codigo} ya tiene bloqueo(s) para función(es) '
                    f'específicas. Revisalos antes de bloquearlo de forma permanente.'
                )

            # Ya existe un bloqueo para esta misma función puntual
            if self.funcion_id and conflictos.filter(funcion_id=self.funcion_id).exists():
                raise ValidationError(
                    f'El asiento {self.asiento_codigo} ya está bloqueado para esta función.'
                )

    def save(self, *args, **kwargs):
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Asiento Bloqueado'
        verbose_name_plural = 'Asientos Bloqueados'
        ordering = ['sala', 'asiento_codigo']
        constraints = [
            models.UniqueConstraint(
                fields=['sala', 'asiento_codigo', 'funcion'],
                name='unico_bloqueo_por_asiento_funcion'
            ),
        ]