# icts/forms.py
from django import forms
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .models import AccessProposal, Participant, ICTSUserProfile, ProposalAttachment, ProposalReview, OLMATRequest
from django.core.exceptions import ValidationError
from .utils import assign_unique_user_siglas

User = get_user_model()


# -----------------------------
# Formularios de PROPUESTA ICTS
# -----------------------------
class AccessProposalForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        # Limitar "previous_access" a propuestas propias ya aceptadas (o al menos del usuario)
        if "previous_access" in self.fields:
            qs = AccessProposal.objects.none()
            if self.request and getattr(self.request, "user", None) and self.request.user.is_authenticated:
                qs = AccessProposal.objects.filter(applicant=self.request.user)
            self.fields["previous_access"].queryset = qs
    class Meta:
        model = AccessProposal
        fields = [
            "title", "scope", "facilities",
            "is_new_request", "previous_access",
            "applicant_is_different", "organization", "contact_person", "email", "phone",
            "project_name", "project_type", "funding_source", "start_year", "end_year",
            "previous_experiments", "references",
            "facility_sem", "facility_sem_fib", "facility_imp", "facility_sims",
            "facility_confocal", "facility_optics", "facility_vdg", "facility_profilometer", "facility_olmat"
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter your project title"}),
            "scope": forms.Textarea(attrs={"rows": 4, "class": "form-control", "placeholder": "Brief description of your project"}),
            "facilities": forms.SelectMultiple(attrs={"class": "form-select"}),
            "organization": forms.TextInput(attrs={"class": "form-control", "placeholder": "Center/Institution"}),
            "contact_person": forms.TextInput(attrs={"class": "form-control", "placeholder": "Contact person name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "contact@example.com"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone number"}),
            "project_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Project name"}),
            "project_type": forms.Select(
                choices=AccessProposal.PROJECT_TYPE_CHOICES,
                attrs={"class": "form-select"}
            ),
            "funding_source": forms.TextInput(attrs={"class": "form-control", "placeholder": "Funding source"}),
            "start_year": forms.NumberInput(attrs={"class": "form-control", "placeholder": "2024"}),
            "end_year": forms.NumberInput(attrs={"class": "form-control", "placeholder": "2025"}),
            "previous_experiments": forms.Textarea(attrs={"rows": 3, "class": "form-control", "placeholder": "Describe previous experiments"}),
            "references": forms.Textarea(attrs={"rows": 3, "class": "form-control", "placeholder": "References and citations"}),
        }


class ParticipantInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            return
        if self.initial_extra and not self.queryset.exists():
            self.extra = max(self.extra, len(self.initial_extra))


ParticipantFormSet = inlineformset_factory(
    parent_model=AccessProposal,
    model=Participant,
    fields=["name", "center", "address"],
    widgets={
        "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full name"}),
        "center": forms.TextInput(attrs={"class": "form-control", "placeholder": "Center/Institution"}),
        "address": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Address"}),
    },
    formset=ParticipantInlineFormSet,
    extra=0,
    can_delete=True,
)

# Validación de adjuntos (tamaño y tipo)
class ProposalAttachmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("name", "file"):
            if field_name in self.fields:
                field = self.fields[field_name]
                field.required = False
                field.widget.attrs.pop("required", None)

    class Meta:
        model = ProposalAttachment
        fields = ["name", "file"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("DELETE"):
            return cleaned
        name = (cleaned.get("name") or "").strip()
        file_obj = cleaned.get("file")
        if name and not file_obj:
            self.add_error("file", "Adjunta el archivo correspondiente.")
        if file_obj and not name:
            self.add_error("name", "Indica un nombre para el adjunto.")
        return cleaned

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if not f and getattr(self.instance, "pk", None) and getattr(self.instance, "file", None):
            return self.instance.file
        if not f:
            return f
        max_mb = 10
        if getattr(f, "size", 0) > max_mb * 1024 * 1024:
            raise forms.ValidationError(f"El archivo supera {max_mb} MB.")

        import os
        ext = os.path.splitext(f.name)[1].lower()
        allowed_exts = {
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg"
        }
        if ext not in allowed_exts:
            raise forms.ValidationError("Tipo de archivo no permitido.")

        ctype = getattr(f, "content_type", "") or ""
        allowed_ctypes = {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "image/png",
            "image/jpeg",
        }
        if ctype and ctype not in allowed_ctypes:
            raise forms.ValidationError("Tipo de contenido no permitido.")
        return f

AttachmentFormSet = inlineformset_factory(
    parent_model=AccessProposal,
    model=ProposalAttachment,
    form=ProposalAttachmentForm,
    fields=["name", "file"],
    widgets={
        "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Document name"}),
        "file": forms.FileInput(attrs={"class": "form-control"}),
    },
    extra=1,
    can_delete=True,
)


# -----------------------------
# Formulario de REGISTRO ICTS
# -----------------------------
class RegistrationICTSForm(UserCreationForm):
    # Campos "de acceso"
    username = forms.CharField(label="Usuario", max_length=150)
    email = forms.EmailField(label="Email")

    # Campos "personales"
    first_name = forms.CharField(label="Nombre", max_length=150)
    last_name = forms.CharField(label="Apellidos", max_length=150)

    # Campos "perfil ICTS"
    institution = forms.CharField(label="Center", max_length=150, required=False)  # ← etiqueta visible "Center"
    phone = forms.CharField(label="Teléfono", max_length=30, required=False)
    address = forms.CharField(
        label="Dirección",
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False
    )

    # Campos CIEMAT
    matricula = forms.CharField(label="Matrícula CIEMAT", max_length=50, required=False)

    accept_terms = forms.BooleanField(
        label="He leído y acepto las condiciones de uso y protección de datos.",
        required=True,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username", "email",
            "first_name", "last_name",
            "password1", "password2",
            "institution", "phone", "address", "matricula", "accept_terms",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe un usuario con ese email.")
        return email

    def clean(self):
        cleaned = super().clean()
        email = (cleaned.get("email") or "").lower().strip()
        is_ciemat = email.endswith("@ciemat.es")
        if is_ciemat:
            # Si es CIEMAT, obliga a completar la matrícula
            if not cleaned.get("matricula"):
                self.add_error("matricula", "Indica la matrícula CIEMAT")
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Campos a los que SÍ queremos añadir la clase Bootstrap
        autostyle = [
            "username", "email", "first_name", "last_name",
            "institution", "phone", "address", "matricula", "password1", "password2",
        ]
        for name in autostyle:
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault("class", "form-control")

    def save(self, commit=True):
        # Usuario inactivo hasta validación manual
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.is_active = False

        if commit:
            user.save()

            # Guardamos institution → en el campo real 'center'
            ICTSUserProfile.objects.create(
                user=user,
                center=self.cleaned_data.get("institution", "").strip(),
                phone=self.cleaned_data.get("phone", "").strip(),
                address=self.cleaned_data.get("address", "").strip(),
                matricula=self.cleaned_data.get("matricula", "").strip(),
                validated=False,
            )

            group, _ = Group.objects.get_or_create(name="icts_users")
            user.groups.add(group)

            # Asignar siglas canónicas al perfil si no existen
            if hasattr(user, "icts_profile") and user.icts_profile and not user.icts_profile.user_siglas:
                assign_unique_user_siglas(user.icts_profile)

        return user


# -----------------------------
# Formulario de REVISIÓN
# -----------------------------
class ProposalReviewForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["decision"].required = False

    def clean_decision(self):
        decision = self.cleaned_data.get("decision")
        return decision or "pending"

    class Meta:
        model = ProposalReview
        fields = [
            "feasibility_ok", 
            "score_scientific_quality", 
            "score_need_infrastructure", 
            "score_industrial_potential",
            "comments", 
            "decision"
        ]
        widgets = {
            "feasibility_ok": forms.RadioSelect(choices=[(True, "Sí, es viable"), (False, "No es viable")]),
            "score_scientific_quality": forms.Select(choices=[("", "Selecciona una puntuación")] + [(i, f"{i} - {'Muy baja' if i==1 else 'Baja' if i==2 else 'Media' if i==3 else 'Alta' if i==4 else 'Excelente'}") for i in range(1, 6)]),
            "score_need_infrastructure": forms.Select(choices=[("", "Selecciona una puntuación")] + [(i, f"{i} - {'No necesita' if i==1 else 'Necesidad baja' if i==2 else 'Necesidad media' if i==3 else 'Necesidad alta' if i==4 else 'Crítica'}") for i in range(1, 6)]),
            "score_industrial_potential": forms.Select(choices=[("", "Selecciona una puntuación")] + [(i, f"{i} - {'Sin interés' if i==1 else 'Bajo interés' if i==2 else 'Interés medio' if i==3 else 'Alto interés' if i==4 else 'Muy alto interés'}") for i in range(1, 6)]),
            "comments": forms.Textarea(attrs={"rows": 6, "class": "form-control", "placeholder": "Proporciona comentarios detallados sobre tu evaluación..."}),
            "decision": forms.Select(choices=[
                ("", "Selecciona tu recomendación"),
                ("approve", "Aprobar - La propuesta cumple con los criterios"),
                ("request_changes", "Solicitar cambios - Necesita modificaciones menores"),
                ("reject", "Rechazar - No cumple con los criterios")
            ])
        }


# -----------------------------
# Formulario específico para OLMAT
# -----------------------------
class OLMATRequestForm(forms.ModelForm):
    class Meta:
        model = OLMATRequest
        fields = [
            "proponent_name",
            "proponent_affiliation",
            "entity_type",
            "activity_description",
            "service_type",
            "irradiation_requirements",
            "diagnostics_needed",
            "sample_preparation",
            "beam_usage",
            "preferred_dates",
            "flexibility",
            "additional_requirements"
        ]
        widgets = {
            "proponent_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nombre del proponente o investigador principal"}
            ),
            "proponent_affiliation": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Centro o institución"}
            ),
            "entity_type": forms.Select(
                choices=[("", "Selecciona el tipo de entidad")] + OLMATRequest.ENTITY_TYPE_CHOICES,
                attrs={"class": "form-select"}
            ),
            "activity_description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "form-control",
                    "placeholder": "Descripción breve (1-2 páginas) con motivación, objetivos y alcance"
                }
            ),
            "service_type": forms.Select(
                choices=[("", "Selecciona el tipo de servicio")] + OLMATRequest.SERVICE_TYPE_CHOICES,
                attrs={"class": "form-select", "required": True}
            ),
            "irradiation_requirements": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Carga térmica prevista, duración de pulsos o cualquier restricción de irradiación (si se conocen)"
                }
            ),
            "preferred_dates": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Especifica las fechas preferidas para el experimento"}
            ),
            "flexibility": forms.Select(
                choices=[
                    ("high", "Alta flexibilidad"),
                    ("medium", "Flexibilidad media"),
                    ("low", "Baja flexibilidad"),
                ],
                attrs={"class": "form-select"}
            ),
            "additional_requirements": forms.Textarea(
                attrs={"rows": 4, "class": "form-control", "placeholder": "Describe cualquier requisito adicional específico para tu experimento con OLMAT"}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ["proponent_name", "proponent_affiliation", "entity_type", "activity_description", "service_type"]:
            self.fields[field].required = True

        self.fields['diagnostics_needed'].required = False
        self.fields['sample_preparation'].required = False
        self.fields['beam_usage'].required = False

        # Configurar campos de diagnóstico como checkboxes
        self.fields['diagnostics_needed'].widget = forms.CheckboxSelectMultiple(
            choices=[
                ("thermocouples", "Termopares"),
                ("pyrometry", "Pirometría"),
                ("thermography", "Termografía infrarroja (resolución 1 ms)"),
                ("fast_camera", "Cámara rápida"),
                ("optical_spectroscopy", "Espectroscopia óptica"),
                ("langmuir_probes", "Sondas Langmuir"),
            ],
            attrs={"class": "form-check-input"}
        )

        self.fields['sample_preparation'].widget = forms.CheckboxSelectMultiple(
            choices=[
                ("liquid_metal_wetting", "Mojado de metal líquido"),
                ("sample_holder_design", "Diseño de portamuestras"),
            ],
            attrs={"class": "form-check-input"}
        )

        self.fields['beam_usage'].widget = forms.CheckboxSelectMultiple(
            choices=[
                ("nbi", "Haz NBI"),
                ("laser", "Láser"),
                ("both", "Ambos"),
            ],
            attrs={"class": "form-check-input"}
        )


class OLMATEvaluationForm(forms.ModelForm):
    """Formulario para que los técnicos de OLMAT evalúen las solicitudes"""
    class Meta:
        model = OLMATRequest
        fields = ["status", "evaluation_notes", "estimated_cost"]
        widgets = {
            "status": forms.Select(
                choices=OLMATRequest.STATUS_CHOICES,
                attrs={"class": "form-select"}
            ),
            "evaluation_notes": forms.Textarea(
                attrs={"rows": 6, "class": "form-control", "placeholder": "Notas de evaluación del equipo OLMAT..."}
            ),
            "estimated_cost": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "placeholder": "Coste estimado en euros"}
            ),
        } 
