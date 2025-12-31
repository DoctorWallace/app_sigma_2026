from django import forms

from icts.models import AccessProposal

from .models import IMPSampleRecord, IMPSession


class IMPSessionCreateForm(forms.ModelForm):
    class Meta:
        model = IMPSession
        fields = ["access_proposal"]
        widgets = {
            "access_proposal": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["access_proposal"].queryset = AccessProposal.objects.filter(
            status="accepted", facility_imp=True
        ).order_by("-created_at")


class IMPSampleRecordForm(forms.ModelForm):
    class Meta:
        model = IMPSampleRecord
        fields = [
            "identification",
            "name",
            "details",
            "received_date",
            "implant_date",
            "return_date",
            "destroyed",
            "destroyed_at",
            "notes",
        ]
        widgets = {
            "identification": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "details": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "received_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "implant_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "return_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "destroyed_at": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class IMPMultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class IMPMessageForm(forms.Form):
    body = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        label="Mensaje",
    )
    attachments = forms.FileField(
        required=False,
        widget=IMPMultiFileInput(attrs={"class": "form-control", "multiple": True}),
        label="Adjuntos",
    )


class IMPFinalReportUploadForm(forms.Form):
    file = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "application/pdf"}),
    )

    def clean_file(self):
        file_obj = self.cleaned_data.get("file")
        if not file_obj:
            return file_obj
        filename = (file_obj.name or "").lower()
        if not filename.endswith(".pdf"):
            raise forms.ValidationError("El informe debe ser un PDF.")
        return file_obj
