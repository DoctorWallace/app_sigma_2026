from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model


DEPARTAMENTOS_CIEMAT = (
    ("LNF", "Laboratorio Nacional de Fusión"),
    ("ENERGIA", "Departamento de Energía"),
    ("MEDIO_AMBIENTE", "Departamento de Medio Ambiente"),
    ("TECNOLOGIA", "Departamento de Tecnología"),
    ("INV_BASICA", "Departamento de Investigación Básica"),
    ("INNOV_BIOMED", "Unidad de Innovación Biomédica"),
    ("FISION", "Unidad de Fisión Nuclear"),
)


User = get_user_model()


class DTFRegisterForm(UserCreationForm):
    # Usar matrícula como username
    username = forms.CharField(max_length=150, label="Número de matrícula")
    first_name = forms.CharField(max_length=150, label="Nombre")
    last_name = forms.CharField(max_length=150, label="Apellidos")
    
    # Departamento obligatorio
    departamento = forms.ChoiceField(
        choices=(("", "Seleccione departamento"),) + DEPARTAMENTOS_CIEMAT,
        required=True,
        label="Departamento",
    )
    
    # Campos adicionales
    division_unidad = forms.CharField(max_length=200, required=False, label="División/Unidad")
    email = forms.EmailField(label="Correo electrónico")
    telefono_interno = forms.CharField(max_length=20, required=False, label="Teléfono interno")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def clean(self):
        cleaned = super().clean()
        # Validar que se seleccione un departamento
        if not cleaned.get("departamento"):
            self.add_error("departamento", "Selecciona un departamento")
        return cleaned

