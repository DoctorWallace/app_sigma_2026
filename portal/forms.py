from django import forms

from .models import DirectServiceRequest


class DirectServiceRequestForm(forms.ModelForm):
    consent = forms.BooleanField(
        required=True,
        label=(
            "Confirmo que los datos son reales, he revisado el formulario y doy "
            "consentimiento para que CIEMAT se ponga en contacto conmigo."
        ),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        error_messages={
            "required": "Debes aceptar el consentimiento para continuar.",
        },
    )

    class Meta:
        model = DirectServiceRequest
        fields = [
            "full_name",
            "email",
            "phone",
            "organization",
            "requested_service",
            "message",
            "form_pdf",
            "is_digitally_signed",
            "consent",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "organization": forms.TextInput(attrs={"class": "form-control"}),
            "requested_service": forms.Select(attrs={"class": "form-select"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "form_pdf": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_digitally_signed": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
