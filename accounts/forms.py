from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError


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

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        allowed = getattr(settings, "DTF_ALLOWED_EMAIL_DOMAINS", ["ciemat.es"])
        allowed_domains = [domain.strip().lower().lstrip("@") for domain in allowed if domain]
        if not any(email.endswith(f"@{domain}") for domain in allowed_domains):
            raise ValidationError("Solo se admite correo corporativo CIEMAT.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Ya existe un usuario con ese correo.")
        return email

    def clean(self):
        cleaned = super().clean()
        # Validar que se seleccione un departamento
        if not cleaned.get("departamento"):
            self.add_error("departamento", "Selecciona un departamento")
        return cleaned
