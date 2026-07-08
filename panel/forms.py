from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from peliculas.models import Pelicula
from salas.models import Sala, Funcion
from reservas.models import Reserva
from promociones.models import Cupon, PromocionDia, Combo

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
        fields = ['nombre', 'filas', 'columnas', 'activa']
        widgets = {
            'nombre':   forms.TextInput(attrs=INPUT_ATTRS),
            'filas':    forms.NumberInput(attrs={**INPUT_ATTRS, 'min': 1, 'max': 26}),
            'columnas': forms.NumberInput(attrs={**INPUT_ATTRS, 'min': 1, 'max': 30}),
            'activa':   forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
        }
        labels = {
            'nombre':   'Nombre de la sala',
            'filas':    'Cantidad de filas (A, B, C...)',
            'columnas': 'Cantidad de columnas (1, 2, 3...)',
            'activa':   'Sala activa',
        }
        help_texts = {
            'filas':    'Máximo 26 filas (A–Z)',
            'columnas': 'La capacidad se calcula automáticamente: filas × columnas',
        }


# ============================================================
# FUNCIONES
# ============================================================
class FuncionForm(forms.ModelForm):
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
            'precio':     forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01', 'min': '0'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
        }
        labels = {
            'pelicula':   'Película',
            'sala':       'Sala',
            'fecha_hora': 'Fecha y hora',
            'precio':     'Precio por entrada ($)',
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
        fields = ['nombre', 'descripcion', 'precio', 'activo', 'imagen']
        widgets = {
            'nombre':      forms.TextInput(attrs=INPUT_ATTRS),
            'descripcion': forms.TextInput(attrs=INPUT_ATTRS),
            'precio':      forms.NumberInput(attrs={**INPUT_ATTRS, 'step': '0.01', 'min': '0'}),
            'activo':      forms.CheckboxInput(attrs={'class': 'panel-checkbox'}),
            'imagen':      forms.ClearableFileInput(attrs={'class': 'panel-file'}),
        }
        labels = {
            'nombre':      'Nombre del combo',
            'descripcion': 'Descripción (Ej: 1 entrada + Pochoclo + Bebida)',
            'precio':      'Precio ($)',
            'activo':      'Combo activo',
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