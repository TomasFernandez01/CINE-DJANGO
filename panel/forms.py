from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from peliculas.models import Pelicula
from salas.models import Sala, Funcion
from reservas.models import Reserva

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