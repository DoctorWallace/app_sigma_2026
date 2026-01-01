from django import forms

from .models import SIMSRecord, SIMSReport, SIMSDocument


class SIMSRecordForm(forms.ModelForm):
    class Meta:
        model = SIMSRecord
        fields = [
            "access_proposal",
            "request_code",
            "reception_date",
            "sample_identification",
            "client_name",
            "sample_characteristics",
            "responsible_name",
            "client_requirements",
            "analysis_date",
            "return_date",
            "incidents",
            "comments",
        ]


class SIMSReportForm(forms.ModelForm):
    class Meta:
        model = SIMSReport
        fields = [
            "delivery_date",
            "determination",
            "procedure_used",
            "technique_text",
            "sample_description",
            "measurement_conditions",
            "results_text",
            "conclusions",
        ]


class SIMSDocumentForm(forms.ModelForm):
    class Meta:
        model = SIMSDocument
        fields = [
            "title",
            "code",
            "version",
            "date",
            "file",
            "is_active",
        ]
