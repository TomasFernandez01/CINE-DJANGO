from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from peliculas.models import Pelicula
from django.forms import inlineformset_factory
from salas.models import Sala, Funcion, SeccionSala
from reservas.models import Reserva
from promociones.models import Cupon, PromocionDia, Combo
from panel.models import ConfiguracionGeneral

# ============================================================
# ESTILOS BASE REUTILIZABLES
# ============================================================
INPUT_CLASS  = 'panel-input'
SELECT_CLASS = 'panel-select'
TEXTAREA_CLASS = 'panel-textarea'

INPUT_ATTRS    = {'class': INPUT_CLASS}
SELECT_ATTRS   = {'class': SELECT_CLASS}
TEXTAREA_ATTRS = {'class': TEXTAREA_CLASS, 'rows': 4}


# ============================================================
# PELÍCULAS
# ============================================================
class PeliculaForm(forms.ModelForm):
    class Meta:
        model = Pelicula
        fields = [
            'titulo', 'sinopsis', 'duracion', 'genero', 'clasificacion',
            'director', 'actores', 'año', 'fecha_estreno', 'en_cartelera', 'poster'
        ]
        widgets = {
            'titulo':        forms.TextInput(attrs=INPUT_ATTRS),
            'sinopsis':      forms.Textarea(attrs=TEXTAREA_ATTRS),
            'duracion':      forms.NumberInput(attrs=INPUT_ATTRS),
            'genero':        forms.Select(attrs=SELECT_ATTRS),
            'clasificacion': forms.Select(attrs=SELECT_ATTRS),
            'director':      forms.TextInput(attrs=INPUT_ATTRS),
            'actores':       forms.Textarea(attrs={**TEXTAREA_ATTRS, 'rows': 3}),
            'año':           forms.NumberInput(attrs=INPUT_ATTRS),
            'fecha_estreno': forms.DateInput(attrs={**INPUT_ATTRS, 'type': 'date'}),
            'en_cartelera':  forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
            'poster':        forms.ClearableFileInput(attrs={'class': 'panel-file'}),
        }
        labels = {
            'titulo':        'Título',
            'sinopsis':      'Sinopsis',
            'duracion':      'Duración (minutos)',
            'genero':        'Género',
            'clasificacion': 'Clasificación',
            'director':      'Director',
            'actores':       'Actores principales',
            'año':           'Año',
            'fecha_estreno': 'Fecha de estreno',
            'en_cartelera':  'En cartelera',
            'poster':        'Poster / Imagen',
        }


# ============================================================
# SALAS
# ============================================================
class SalaForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ['nombre', 'tipo', 'filas', 'columnas', 'multiplicador_precio', 'activa']
        widgets = {
            'nombre':   forms.TextInput(attrs=INPUT_ATTRS),
            'tipo':     forms.Select(attrs=SELECT_ATTRS),
            'filas':    forms.NumberInput(attrs={**INPUT_ATTRS, 'min': 1, 'max': 26}),
            'columnas': forms.NumberInput(attrs={**INPUT_ATTRS, 'min': 1, 'max': 30}),
            'multiplicador_precio': forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01', 'min': '0.01', 'id': 'id_multiplicador_precio'}),
            'activa':   forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
        }
        labels = {
            'nombre':   'Nombre de la sala',
            'tipo':     'Tipo de sala',
            'filas':    'Filas totales del lienzo (A, B, C...)',
            'columnas': 'Columnas totales del lienzo',
            'multiplicador_precio': 'Multiplicador de precio',
            'activa':   'Sala activa',
        }
        help_texts = {
            'filas':    'Máximo 26 filas (A-Z). Debe alcanzar para la sección más profunda.',
            'columnas': 'Debe alcanzar para el ancho total (todas las secciones + pasillos).',
            'tipo':     'Al elegir el tipo se sugiere un multiplicador (podés cambiarlo igual).',
            'multiplicador_precio': 'Se aplica sobre el precio base de la entrada. 1.00 = precio normal.',
        }
# ============================================================
# SALAS — SECCIONES (formset inline)
# ============================================================
SeccionSalaFormSet = inlineformset_factory(
    Sala,
    SeccionSala,
    fields=['nombre', 'fila_inicio', 'fila_fin', 'columna_inicio', 'columna_fin'],
    extra=1,
    can_delete=True,
    widgets={
        'nombre': forms.TextInput(attrs={**INPUT_ATTRS, 'placeholder': 'Ej: Centro, Lateral Izquierdo'}),
        'fila_inicio': forms.NumberInput(attrs={**INPUT_ATTRS, 'min': 1}),
        'fila_fin': forms.NumberInput(attrs={**INPUT_ATTRS, 'min': 1}),
        'columna_inicio': forms.NumberInput(attrs={**INPUT_ATTRS, 'min': 1}),
        'columna_fin': forms.NumberInput(attrs={**INPUT_ATTRS, 'min': 1}),
    },
)

# ============================================================
# FUNCIONES
# ============================================================
class FuncionForm(forms.ModelForm):
    # Declarado explícito (no solo inferido de blank=True del modelo) para
    # que quede 100% claro y no dependa de que el estado de la migración
    # coincida exactamente con models.py: precio SIEMPRE es opcional acá.
    precio = forms.DecimalField(
        required=False, max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01', 'min': '0',
                                          'placeholder': 'Vacío = automático (precio base x multiplicador de sala)'}),
        label='Precio por entrada ($) — opcional',
        help_text='Dejalo vacío para que se calcule solo: precio base configurado x multiplicador de la sala.'
    )
    class Meta:
        model = Funcion
        fields = ['pelicula', 'sala', 'fecha_hora', 'precio', 'disponible']
        widgets = {
            'pelicula':   forms.Select(attrs=SELECT_ATTRS),
            'sala':       forms.Select(attrs=SELECT_ATTRS),
            'fecha_hora': forms.DateTimeInput(
                attrs={**INPUT_ATTRS, 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            # 'precio':forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01', 'min': '0', 'placeholder': 'Vacío = automático (precio base x multiplicador de sala)'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
        }
        labels = {
            'pelicula':   'Película',
            'sala':       'Sala',
            'fecha_hora': 'Fecha y hora',
            # 'precio':     'Precio por entrada ($) — opcional',
            'disponible': 'Disponible para reservas',
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Formatear la fecha correctamente para el input datetime-local
        if self.instance and self.instance.pk and self.instance.fecha_hora:
            self.initial['fecha_hora'] = self.instance.fecha_hora.strftime('%Y-%m-%dT%H:%M')
        # Solo películas en cartelera
        self.fields['pelicula'].queryset = Pelicula.objects.filter(
            en_cartelera=True
        ).order_by('titulo')

# ============================================================
# USUARIOS
# ============================================================
class CrearUsuarioForm(UserCreationForm):
    """Para crear nuevos usuarios desde el panel."""
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs=INPUT_ATTRS),
        label='Email'
    )
    first_name = forms.CharField(
        max_length=30, required=False,
        widget=forms.TextInput(attrs=INPUT_ATTRS),
        label='Nombre'
    )
    last_name = forms.CharField(
        max_length=30, required=False,
        widget=forms.TextInput(attrs=INPUT_ATTRS),
        label='Apellido'
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'password1', 'password2', 'is_staff', 'is_active'
        ]
        widgets = {
            'username':  forms.TextInput(attrs=INPUT_ATTRS),
            'is_staff':  forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
        }
        labels = {
            'username':  'Nombre de usuario',
            'is_staff':  'Puede acceder al panel (staff)',
            'is_active': 'Cuenta activa',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(attrs=INPUT_ATTRS)
        self.fields['password2'].widget = forms.PasswordInput(attrs=INPUT_ATTRS)
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Confirmar contraseña'


class EditarUsuarioForm(forms.ModelForm):
    """Para editar usuarios existentes (sin cambiar contraseña)."""
    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'is_staff', 'is_superuser', 'is_active'
        ]
        widgets = {
            'username':     forms.TextInput(attrs=INPUT_ATTRS),
            'first_name':   forms.TextInput(attrs=INPUT_ATTRS),
            'last_name':    forms.TextInput(attrs=INPUT_ATTRS),
            'email':        forms.EmailInput(attrs=INPUT_ATTRS),
            'is_staff':     forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
            'is_active':    forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
        }
        labels = {
            'username':     'Nombre de usuario',
            'first_name':   'Nombre',
            'last_name':    'Apellido',
            'email':        'Email',
            'is_staff':     'Puede acceder al panel (staff)',
            'is_superuser': 'Superusuario (acceso total)',
            'is_active':    'Cuenta activa',
        }

# ============================================================
# AGREGAR ESTA CLASE AL FINAL DE panel/forms.py
# También agregar el import: from reservas.models import Reserva
# ============================================================

class ReservaForm(forms.ModelForm):
    """
    Formulario para editar una reserva desde el panel.
    El staff puede cambiar estado, ajustar fecha límite y corregir asientos.
    """
    class Meta:
        model = Reserva
        fields = ['estado', 'asientos_seleccionados', 'fecha_limite_pago']
        widgets = {
            'estado': forms.Select(attrs=SELECT_ATTRS),
            'asientos_seleccionados': forms.TextInput(attrs={
                **INPUT_ATTRS,
                'placeholder': 'Ej: A1,A2,B5',
            }),
            'fecha_limite_pago': forms.DateTimeInput(
                attrs={**INPUT_ATTRS, 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
        }
        labels = {
            'estado':                'Estado de la reserva',
            'asientos_seleccionados': 'Asientos (separados por coma)',
            'fecha_limite_pago':     'Fecha límite de pago',
        }
        help_texts = {
            'asientos_seleccionados': 'Dejá vacío si no aplica. La cantidad de entradas se actualiza automáticamente.',
            'fecha_limite_pago':      'Solo relevante para reservas pendientes.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.fecha_limite_pago:
            self.initial['fecha_limite_pago'] = self.instance.fecha_limite_pago.strftime('%Y-%m-%dT%H:%M')

# ============================================================
# PROMOCIONES — COMBOS
# ============================================================
class ComboForm(forms.ModelForm):
    class Meta:
        model = Combo
        # modificado (combos múltiples): se suma categoria
        fields = ['nombre', 'descripcion', 'precio','categoria', 'activo', 'imagen']
        widgets = {
            'nombre':      forms.TextInput(attrs=INPUT_ATTRS),
            'descripcion': forms.TextInput(attrs=INPUT_ATTRS),
            'precio':      forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01', 'min': '0'}),
            'categoria':   forms.Select(attrs=INPUT_ATTRS),
            'activo':      forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
            'imagen':      forms.ClearableFileInput(attrs={'class': 'panel-file'}),
        }
        labels = {
            'nombre':      'Nombre del item',
            'descripcion': 'Descripción (Ej: 1 entrada + Pochoclo + Bebida)',
            'precio':      'Precio ($)',
            'categoria':   'Categoría',
            # 'activo':      'Combo activo',
            'imagen':      'Imagen',
        }


# ============================================================
# PROMOCIONES — CUPONES
# ============================================================
class CuponForm(forms.ModelForm):
    class Meta:
        model = Cupon
        fields = [
            'codigo', 'descripcion', 'tipo', 'valor',
            'fecha_inicio', 'fecha_fin', 'usos_maximos',
            'monto_minimo', 'solo_primera_compra', 'activo',
        ]
        widgets = {
            'codigo':       forms.TextInput(attrs={**INPUT_ATTRS, 'placeholder': 'Ej: VERANO10', 'style': 'text-transform:uppercase;'}),
            'descripcion':  forms.TextInput(attrs=INPUT_ATTRS),
            'tipo':         forms.Select(attrs=SELECT_ATTRS),
            'valor':        forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01', 'min': '0'}),
            'fecha_inicio': forms.DateInput(attrs={**INPUT_ATTRS, 'type': 'date'}),
            'fecha_fin':    forms.DateInput(attrs={**INPUT_ATTRS, 'type': 'date'}),
            'usos_maximos': forms.NumberInput(attrs={**INPUT_ATTRS, 'min': '0'}),
            'monto_minimo': forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01', 'min': '0'}),
            'solo_primera_compra': forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
            'activo':       forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
        }
        labels = {
            'codigo':              'Código',
            'descripcion':         'Descripción',
            'tipo':                'Tipo de descuento',
            'valor':               'Valor',
            'fecha_inicio':        'Fecha de inicio',
            'fecha_fin':           'Fecha de fin',
            'usos_maximos':        'Usos máximos',
            'monto_minimo':        'Monto mínimo de compra',
            'solo_primera_compra': 'Solo primera compra',
            'activo':              'Cupón activo',
        }
        help_texts = {
            'valor':        'Si es porcentaje: 25 = 25%. Si es monto fijo: 500 = $500',
            'usos_maximos': 'Dejar vacío para usos ilimitados',
            'monto_minimo': 'Dejar vacío si no aplica',
        }


# ============================================================
# PROMOCIONES — PROMOCIÓN POR DÍA
# ============================================================
class PromocionDiaForm(forms.ModelForm):
    class Meta:
        model = PromocionDia
        fields = ['nombre', 'dia_semana', 'tipo', 'porcentaje_descuento', 'descripcion', 'activo']
        widgets = {
            'nombre':                forms.TextInput(attrs=INPUT_ATTRS),
            'dia_semana':            forms.Select(attrs=SELECT_ATTRS),
            'tipo':                  forms.Select(attrs=SELECT_ATTRS),
            'porcentaje_descuento':  forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01', 'min': '0'}),
            'descripcion':           forms.Textarea(attrs={**TEXTAREA_ATTRS, 'rows': 3}),
            'activo':                forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
        }
        labels = {
            'nombre':               'Nombre de la promoción',
            'dia_semana':           'Día de la semana',
            'tipo':                 'Tipo',
            'porcentaje_descuento': '% de descuento',
            'descripcion':          'Descripción (visible para el usuario)',
            'activo':               'Promoción activa',
        }
        help_texts = {
            'porcentaje_descuento': 'Solo aplica si el tipo es "Descuento porcentual"',
        }

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================
# modificado (Hilo 1 - Tanda D): se agregaron los campos que antes eran
# constantes hardcodeadas en configuracion/settings.py.
class ConfiguracionGeneralForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionGeneral
        fields = [
            'precio_entrada_base',
            'tiempo_limite_pago_minutos', 'max_asientos_por_reserva', 'qr_minutos_antes_funcion',
            'tmdb_api_key',
            'email_backend', 'email_host', 'email_port', 'email_use_tls',
            'email_host_user', 'email_host_password', 'email_from',
        ]
        widgets = {
            'precio_entrada_base': forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01', 'min': '0'}),
            'tiempo_limite_pago_minutos': forms.NumberInput(attrs={**INPUT_ATTRS, 'min': '1'}),
            'max_asientos_por_reserva': forms.NumberInput(attrs={**INPUT_ATTRS, 'min': '1'}),
            'qr_minutos_antes_funcion': forms.NumberInput(attrs={**INPUT_ATTRS, 'min': '0'}),
            'tmdb_api_key': forms.TextInput(attrs={**INPUT_ATTRS, 'placeholder': 'Dejar vacío para usar la de settings.py'}),
            'email_backend': forms.Select(attrs=SELECT_ATTRS),
            'email_host': forms.TextInput(attrs={**INPUT_ATTRS, 'placeholder': 'smtp.gmail.com'}),
            'email_port': forms.NumberInput(attrs={**INPUT_ATTRS, 'min': '1', 'placeholder': '587'}),
            'email_host_user': forms.TextInput(attrs=INPUT_ATTRS),
            'email_host_password': forms.PasswordInput(attrs=INPUT_ATTRS, render_value=True),
            'email_from': forms.TextInput(attrs={**INPUT_ATTRS, 'placeholder': 'Cine Online <noreply@cineonline.com>'}),
        }
        labels = {
            'precio_entrada_base': 'Precio base de la entrada ($)',
            'tiempo_limite_pago_minutos': 'Tiempo límite de pago (minutos)',
            'max_asientos_por_reserva': 'Máximo de asientos por reserva',
            'qr_minutos_antes_funcion': 'Habilitar QR desde (minutos antes de la función)',
            'tmdb_api_key': 'API key de TMDB',
            'email_backend': 'Modo de envío de emails',
            'email_host': 'Servidor SMTP (host)',
            'email_port': 'Puerto SMTP',
            'email_use_tls': 'Usar TLS',
            'email_host_user': 'Usuario SMTP',
            'email_host_password': 'Contraseña SMTP',
            'email_from': 'Remitente ("De:")',
        }
        help_texts = {
            'precio_entrada_base': 'Se usa para las funciones que no tengan un precio manual cargado '
                                     '(se multiplica por el multiplicador de la sala).',
            'tiempo_limite_pago_minutos': 'Se cuenta desde que el usuario entra a seleccionar asientos.',
            'max_asientos_por_reserva': 'Por operación de reserva, no por usuario en total.',
            'qr_minutos_antes_funcion': 'Ejemplo: 120 = se puede escanear desde 2 horas antes de la función.',
            'tmdb_api_key': 'Se usa en Panel > Películas > Buscar en TMDB.',
            'email_host_password': 'Se guarda en texto plano en la base — mismo nivel de seguridad que '
                                     'tenía hardcodeado en settings.py.',
        }

