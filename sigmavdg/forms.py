from django import forms

from icts.models import AccessProposal

from .models import (
    VDGEquipment,
    VDGEquipmentDocument,
    VDGEquipmentIncident,
    VDGItem,
    VDGItemMovement,
    VDGSampleRecord,
    VDGSession,
)


class VDGSessionCreateForm(forms.ModelForm):
    class Meta:
        model = VDGSession
        fields = ["access_proposal"]
        widgets = {
            "access_proposal": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["access_proposal"].queryset = AccessProposal.objects.filter(
            status="accepted", facility_vdg=True
        ).order_by("-created_at")


class VDGSessionUpdateForm(forms.ModelForm):
    class Meta:
        model = VDGSession
        fields = [
            "received_date",
            "irradiation_start_date",
            "irradiation_end_date",
            "report_issue_date",
            "report_delivery_date",
            "observations",
        ]
        widgets = {
            "received_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "irradiation_start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "irradiation_end_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "report_issue_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "report_delivery_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "observations": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class VDGSampleRecordForm(forms.ModelForm):
    class Meta:
        model = VDGSampleRecord
        fields = [
            "code",
            "material",
            "electron_fluence",
            "temperature",
            "atmosphere",
            "sample_size",
            "sample_geometry",
            "fluence_result",
            "current_na",
            "time_minutes",
            "notes",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "material": forms.TextInput(attrs={"class": "form-control"}),
            "electron_fluence": forms.TextInput(attrs={"class": "form-control"}),
            "temperature": forms.TextInput(attrs={"class": "form-control"}),
            "atmosphere": forms.TextInput(attrs={"class": "form-control"}),
            "sample_size": forms.TextInput(attrs={"class": "form-control"}),
            "sample_geometry": forms.TextInput(attrs={"class": "form-control"}),
            "fluence_result": forms.TextInput(attrs={"class": "form-control"}),
            "current_na": forms.TextInput(attrs={"class": "form-control"}),
            "time_minutes": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class VDGEquipmentForm(forms.ModelForm):
    class Meta:
        model = VDGEquipment
        fields = [
            "code",
            "description",
            "is_reference",
            "responsible",
            "location",
            "received_date",
            "decommission_date",
            "brand",
            "model",
            "serial_number",
            "range",
            "resolution",
            "tolerance",
            "observations",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_reference": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "responsible": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "received_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "decommission_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "brand": forms.TextInput(attrs={"class": "form-control"}),
            "model": forms.TextInput(attrs={"class": "form-control"}),
            "serial_number": forms.TextInput(attrs={"class": "form-control"}),
            "range": forms.TextInput(attrs={"class": "form-control"}),
            "resolution": forms.TextInput(attrs={"class": "form-control"}),
            "tolerance": forms.TextInput(attrs={"class": "form-control"}),
            "observations": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class VDGEquipmentDocumentForm(forms.ModelForm):
    class Meta:
        model = VDGEquipmentDocument
        fields = ["doc_type", "file", "date", "notes"]
        widgets = {
            "doc_type": forms.Select(attrs={"class": "form-control"}),
            "file": forms.FileInput(attrs={"class": "form-control"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class VDGEquipmentIncidentForm(forms.ModelForm):
    class Meta:
        model = VDGEquipmentIncident
        fields = ["date", "severity", "status", "description", "attachment"]
        widgets = {
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "severity": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "attachment": forms.FileInput(attrs={"class": "form-control"}),
        }


class VDGItemForm(forms.ModelForm):
    class Meta:
        model = VDGItem
        fields = ["code", "description", "active"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class VDGItemMovementOutForm(forms.ModelForm):
    class Meta:
        model = VDGItemMovement
        fields = [
            "item",
            "fecha_salida",
            "motivo_salida",
            "forma_envio",
            "destino",
            "responsable_destino",
            "cumplimentado_por_salida",
            "notas",
        ]
        widgets = {
            "item": forms.Select(attrs={"class": "form-control"}),
            "fecha_salida": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "motivo_salida": forms.TextInput(attrs={"class": "form-control"}),
            "forma_envio": forms.TextInput(attrs={"class": "form-control"}),
            "destino": forms.TextInput(attrs={"class": "form-control"}),
            "responsable_destino": forms.TextInput(attrs={"class": "form-control"}),
            "cumplimentado_por_salida": forms.TextInput(attrs={"class": "form-control"}),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class VDGItemMovementInForm(forms.ModelForm):
    class Meta:
        model = VDGItemMovement
        fields = [
            "fecha_entrada",
            "estado_recepcion",
            "estado_recepcion_detalle",
            "cumplimentado_por_entrada",
            "notas",
        ]
        widgets = {
            "fecha_entrada": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "estado_recepcion": forms.Select(attrs={"class": "form-control"}),
            "estado_recepcion_detalle": forms.TextInput(attrs={"class": "form-control"}),
            "cumplimentado_por_entrada": forms.TextInput(attrs={"class": "form-control"}),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        fecha_entrada = cleaned.get("fecha_entrada")
        if fecha_entrada and self.instance and self.instance.fecha_salida:
            if fecha_entrada < self.instance.fecha_salida:
                self.add_error(
                    "fecha_entrada",
                    "La fecha de entrada no puede ser anterior a la fecha de salida.",
                )
        estado = cleaned.get("estado_recepcion")
        detalle = (cleaned.get("estado_recepcion_detalle") or "").strip()
        if estado == "other" and not detalle:
            self.add_error(
                "estado_recepcion_detalle",
                "Indica un detalle cuando el estado es 'Otro'.",
            )
        return cleaned
