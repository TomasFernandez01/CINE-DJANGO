from django.db import models
from peliculas.models import Pelicula
from sedes.models import Sede
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP


def redondear_precio(monto, paso=Decimal('50')):
    monto = Decimal(monto)
    return (monto / paso).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * paso

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
    # nuevo (Sedes - Fase 1): a qué sede pertenece esta sala. PROTECT en vez
    # de CASCADE a propósito — borrar una Sede no debería poder arrastrarse
    # y borrar en cascada todas sus salas/funciones/reservas/pagos; si se
    # quiere dar de baja una sede, se desactiva (Sede.activa=False) o se
    # borran sus salas explícitamente primero.
    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        related_name='salas',
        help_text="Sede física a la que pertenece esta sala."
    )
    nombre = models.CharField(max_length=100,default='SALA')
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
        default=10, 
        help_text=
                "Cantidad TOTAL de filas del lienzo de la sala (A, B, C, ...). "
                "Si la sala tiene secciones, ninguna puede exceder este valor."
        )
    columnas = models.IntegerField(
        default=10, 
        help_text=
                "Cantidad TOTAL de columnas del lienzo de la sala (1, 2, 3, ...). "
                "Si la sala tiene secciones, ninguna puede exceder este valor."
        )
    
    multiplicador_precio = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('1.00'),
        help_text="Multiplica el precio base de la entrada para funciones en esta "
                   "sala (1.00 = precio normal, 1.25 = +25%, etc). Libre: podés "
                   "usar el valor sugerido de tu tipo de sala o poner cualquier otro."
    )
    
    def __str__(self):
        return f"{self.nombre} [{self.get_tipo_display()}] (Cap: {self.capacidad})"
 
    def tipo_icono(self):
        return self.TIPO_CONFIG.get(self.tipo, {}).get('icono', '🎬')
 
    def tipo_color(self):
        return self.TIPO_CONFIG.get(self.tipo, {}).get('color', '#6c757d')
 
    def tipo_multiplicador_sugerido(self):
        """Multiplicador sugerido según el tipo de sala (2D/3D/Premium), solo
        como referencia para precargar el campo libre multiplicador_precio."""
        return self.TIPO_CONFIG.get(self.tipo, {}).get('multiplicador', Decimal('1.00'))

    def es_premium(self):
        return 'premium' in self.tipo
 
    def es_3d(self):
        return '3d' in self.tipo
    
    def layout_asientos(self):
        """Retorna el layout de asientos """
        letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        secciones = list(self.secciones.all()) if self.pk else []

        if not secciones:
            layout = []
            for i in range(self.filas):
                celdas = [f"{letras[i]}{j}" for j in range(1, self.columnas + 1)]
                layout.append({'letra': letras[i], 'celdas': celdas})
            return layout
        
        layout = []
        for fila_num in range(1, self.filas + 1):
            fila_celdas = []
            for col_num in range(1, self.columnas + 1):
                cubierta = any(
                    s.fila_inicio <= fila_num <= s.fila_fin and
                    s.columna_inicio <= col_num <= s.columna_fin
                    for s in secciones
                )
                fila_celdas.append(f"{letras[fila_num - 1]}{col_num}" if cubierta else None)
            if any(fila_celdas):
                layout.append({'letra': letras[fila_num - 1], 'celdas': fila_celdas})
        return layout
    
    def total_asientos(self):
        secciones = list(self.secciones.all()) if self.pk else []
        if not secciones:
            return self.filas * self.columnas
        return sum(s.total_asientos() for s in secciones)
    
    def save(self, *args, **kwargs):
        # Auto-ajustar capacidad si no está definida
        if not self.capacidad or self.capacidad != self.total_asientos():
            self.capacidad = self.total_asientos()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Sala'
        verbose_name_plural = 'Salas'
        ordering = ['nombre']

# ==========================================================================
class SeccionSala(models.Model):
    """
    Una región rectangular dentro del lienzo (filas x columnas) de una Sala.
    Varias secciones pueden convivir lado a lado o con distinta profundidad
    de filas (ej: sector central que llega más atrás que los laterales).
    Las celdas del lienzo que no están cubiertas por ninguna sección quedan
    vacías (pasillos).
    """
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='secciones')
    nombre = models.CharField(
        max_length=50,
        help_text="Ej: Lateral Izquierdo, Centro, Palcos"
    )
    fila_inicio = models.PositiveIntegerField(help_text="Primera fila (1 = A, 2 = B, ...)")
    fila_fin = models.PositiveIntegerField(help_text="Última fila incluida")
    columna_inicio = models.PositiveIntegerField(help_text="Primera columna")
    columna_fin = models.PositiveIntegerField(help_text="Última columna incluida")

    def __str__(self):
        return (f"{self.sala.nombre} - {self.nombre} "
                f"(filas {self.fila_inicio}-{self.fila_fin}, "
                f"columnas {self.columna_inicio}-{self.columna_fin})")

    def total_asientos(self):
        """Cantidad de asientos que ocupa esta sección (área del rectángulo)."""
        return (self.fila_fin - self.fila_inicio + 1) * (self.columna_fin - self.columna_inicio + 1)

    def clean(self):
        super().clean()

        # 1. Rangos coherentes
        if self.fila_inicio and self.fila_fin and self.fila_inicio > self.fila_fin:
            raise ValidationError({'fila_fin': 'La fila final no puede ser menor a la fila inicial.'})
        if self.columna_inicio and self.columna_fin and self.columna_inicio > self.columna_fin:
            raise ValidationError({'columna_fin': 'La columna final no puede ser menor a la columna inicial.'})

        # 2. No exceder el lienzo total de la sala
        if self.sala_id:
            if self.fila_fin and self.fila_fin > self.sala.filas:
                raise ValidationError({
                    'fila_fin': f'La sala "{self.sala.nombre}" solo tiene {self.sala.filas} filas en total.'
                })
            if self.columna_fin and self.columna_fin > self.sala.columnas:
                raise ValidationError({
                    'columna_fin': f'La sala "{self.sala.nombre}" solo tiene {self.sala.columnas} columnas en total.'
                })
            if self.fila_inicio and self.fila_inicio < 1:
                raise ValidationError({'fila_inicio': 'La fila inicial debe ser 1 o mayor.'})
            if self.columna_inicio and self.columna_inicio < 1:
                raise ValidationError({'columna_inicio': 'La columna inicial debe ser 1 o mayor.'})

        # 3. No solaparse con otra sección de la misma sala
        if self.sala_id and self.fila_inicio and self.fila_fin and self.columna_inicio and self.columna_fin:
            otras = SeccionSala.objects.filter(sala_id=self.sala_id)
            if self.pk:
                otras = otras.exclude(pk=self.pk)

            for otra in otras:
                filas_se_solapan = not (self.fila_fin < otra.fila_inicio or self.fila_inicio > otra.fila_fin)
                columnas_se_solapan = not (self.columna_fin < otra.columna_inicio or self.columna_inicio > otra.columna_fin)
                if filas_se_solapan and columnas_se_solapan:
                    raise ValidationError(
                        f'Esta sección se superpone con "{otra.nombre}" '
                        f'(filas {otra.fila_inicio}-{otra.fila_fin}, '
                        f'columnas {otra.columna_inicio}-{otra.columna_fin}).'
                    )

    def save(self, *args, **kwargs):
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)
        # La capacidad de la sala depende de sus secciones: recalcular.
        self.sala.save()

    def delete(self, *args, **kwargs):
        sala = self.sala
        super().delete(*args, **kwargs)
        sala.save()  # recalcular capacidad tras borrar la sección

    class Meta:
        verbose_name = 'Sección de Sala'
        verbose_name_plural = 'Secciones de Sala'
        ordering = ['sala', 'fila_inicio', 'columna_inicio']

# ==========================================================================


class Funcion(models.Model):
    pelicula = models.ForeignKey(Pelicula, on_delete=models.CASCADE, related_name='funciones')
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name='funciones')
    fecha_hora = models.DateTimeField()
    precio = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, #<= esto faltaba
        help_text="Precio manual de esta función. Si lo dejás vacío, se calcula "
                   "automáticamente: precio base configurado x multiplicador de "
                   "la sala."
    )
    disponible = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.pelicula.titulo} - {self.sala.nombre} [{self.sala.get_tipo_display()}] - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"

    def precio_final(self):
        """
        Precio final de la función: el manual si el admin cargó uno, sino el
        calculado automáticamente (precio base configurable x multiplicador
        de la sala), redondeado a un valor cerrado.
        """
        if self.precio is not None:
            return self.precio
        # modificado (T11): se pasa la sede de esta sala para respetar su
        # ConfiguracionGeneral propia (T9) si existe. Sin fila propia,
        # obtener() cae solo a la global, igual que antes.
        # BUGFIX (post-T11): Funcion no tiene un campo `sede` propio -- la
        # sede se llega vía self.sala.sede (FK Sala -> Sede). El `self.sede`
        # original tiraba AttributeError cada vez que se llamaba
        # precio_final() (usado en /funciones/, /mis-reservas/, detalle de
        # película, checkout, etc. -- básicamente en todos lados donde se
        # muestra un precio), rompiendo esas páginas por completo.
        from panel.models import ConfiguracionGeneral
        base = ConfiguracionGeneral.obtener(sede=self.sala.sede).precio_entrada_base
        return redondear_precio(base * self.sala.multiplicador_precio)

    def precio_para_asiento(self, codigo_asiento):
        """
        Precio final de UN asiento puntual: el precio_final() de la función,
        multiplicado además por el multiplicador de su categoría si ese
        asiento tiene una CategoriaAsiento asignada (ej: "Mejorado" x1.25).
        Los multiplicadores se van aplicando en cadena (sala, luego asiento),
        no se reemplazan entre sí — así el sistema queda simple y predecible
        para cuando se sumen más modificadores de precio a futuro.
        """
        precio_base = self.precio_final()
        categoria = self.sala.categorias_asientos.filter(asiento_codigo=codigo_asiento).first()
        if categoria:
            return redondear_precio(precio_base * categoria.multiplicador)
        return precio_base

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
    
    def asientos_bloqueados_por_motivo(self, motivo):
        """
        Igual que asientos_bloqueados(), pero filtrado por motivo
        ('mantenimiento' o 'reservado').
        """
        bloqueos = self.sala.bloqueos_asientos.filter(
            models.Q(funcion__isnull=True) | models.Q(funcion=self),
            motivo=motivo,
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

class AsientoBloqueado(models.Model):
    MOTIVO_CHOICES = [
        ('mantenimiento', 'Mantenimiento'),
        ('reservado', 'Reservado'),
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
    motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES, default='mantenimiento')
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
                # asiento
                # for fila in self.sala.layout_asientos()
                # for asiento in fila
                codigo
                for fila in self.sala.layout_asientos()
                for codigo in fila['celdas']
                if codigo is not None
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
            
            # 4. Un asiento bloqueado de forma PERMANENTE no puede tener también
            #    una categoría especial (serían dos estados contradictorios).
            if self.funcion_id is None and self.sala.categorias_asientos.filter(
                    asiento_codigo=self.asiento_codigo).exists():
                raise ValidationError(
                    f'El asiento {self.asiento_codigo} tiene una categoría especial '
                    f'asignada (ej: Mejorado). Sacale esa categoría antes de bloquearlo '
                    f'de forma permanente.'
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


########################################################################
class CategoriaAsiento(models.Model):
    """
    Categoría especial para un asiento puntual (ej: "Mejorado"), que a
    diferencia de AsientoBloqueado NO impide comprarlo — solo le cambia el
    precio (vía `multiplicador`, aplicado sobre Funcion.precio_final()) y el
    color en el mapa. Es permanente por sala (no depende de una función
    puntual), a diferencia de los bloqueos que sí pueden ser por función.
    """
    sala = models.ForeignKey(
        Sala,
        on_delete=models.CASCADE,
        related_name='categorias_asientos'
    )
    asiento_codigo = models.CharField(
        max_length=10,
        help_text="Código del asiento, ej: A1"
    )
    nombre = models.CharField(
        max_length=50, default='Mejorado',
        help_text="Nombre de la categoría, ej: Mejorado, Confort, Primera fila"
    )
    multiplicador = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal('1.25'),
        help_text="Se aplica sobre el precio final de la función para este asiento "
                   "puntual (1.25 = +25%, 1.50 = +50%, etc)."
    )
    color = models.CharField(
        max_length=7, default='#f1c40f',
        help_text="Color hex para mostrar este asiento en el mapa, ej: #f1c40f"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sala.nombre} - {self.asiento_codigo} ({self.nombre} x{self.multiplicador})"

    def clean(self):
        super().clean()

        # 1. Validar que el asiento_codigo exista realmente en la sala
        if self.sala_id and self.asiento_codigo:
            codigos_validos = {
                codigo
                for fila in self.sala.layout_asientos()
                for codigo in fila['celdas']
                if codigo is not None
            }
            if self.asiento_codigo not in codigos_validos:
                raise ValidationError({
                    'asiento_codigo': f'"{self.asiento_codigo}" no existe en la sala '
                                       f'"{self.sala.nombre}". Códigos válidos: '
                                       f'{", ".join(sorted(codigos_validos))}.'
                })

        # 2. Un asiento con categoría especial no puede estar bloqueado de
        #    forma permanente al mismo tiempo (son estados contradictorios).
        if self.sala_id and self.asiento_codigo:
            if self.sala.bloqueos_asientos.filter(
                    asiento_codigo=self.asiento_codigo, funcion__isnull=True).exists():
                raise ValidationError(
                    f'El asiento {self.asiento_codigo} tiene un bloqueo permanente '
                    f'(mantenimiento/reservado). Sacale ese bloqueo antes de asignarle '
                    f'una categoría.'
                )

    def save(self, *args, **kwargs):
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Categoría de Asiento'
        verbose_name_plural = 'Categorías de Asientos'
        ordering = ['sala', 'asiento_codigo']
        constraints = [
            models.UniqueConstraint(
                fields=['sala', 'asiento_codigo'],
                name='unica_categoria_por_asiento'
            ),
        ]