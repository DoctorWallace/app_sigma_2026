from django import forms
from django.contrib.auth.models import User
from .models import (
    ConfocalSolicitud,
    ConfocalMuestraIndividual,
    ConfocalAvance,
    ConfocalDiarioEntrada,
    LO3Attachment,
    LO3Calibration,
    LO3Equipment,
    LO3EquipmentDocument,
    LO3ReferenceMaterial,
    LO3ReferenceMaterialDocument,
    LO3Incident,
    LO3IncidentAttachment,
    LO3Habilitation,
    MCFSession,
    MCFSampleRecord,
)
from sigmalab.models import UsuarioAsociado
from icts.models import AccessProposal


class ConfocalSolicitudForm(forms.ModelForm):
    """Formulario para crear solicitudes de microscopía confocal"""
    
    class Meta:
        model = ConfocalSolicitud
        fields = [
            'material', 'numero_muestras', 'tipo_microscopia',
            'longitud_onda_excitacion', 'longitud_onda_emision', 
            'objetivo_requerido', 'espesor_muestra',
            'tincion_utilizada', 'preparacion_muestra',
            'material_radioactivo', 'manejo_especial', 'tratamiento_previo',
            'procedencia', 'otro_dato_importante',
            'requisitos_finales', 'observaciones',
            'imagen_muestra', 'croquis',
            'tiempo_estimado_numero', 'tiempo_estimado_unidad', 'tiempo_estimado_indeterminado',
            'montaje_fluorescente', 'fijacion', 'deshidratacion', 'inclusion',
            'corte_fino', 'tincion_histologica', 'inmunotincion', 'tincion_nuclear',
            'becario_asociado'
        ]
        widgets = {
            'material': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_muestras': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'tipo_microscopia': forms.Select(attrs={'class': 'form-control'}),
            'longitud_onda_excitacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ej: 488nm, 561nm'}),
            'longitud_onda_emision': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ej: 500-550nm'}),
            'objetivo_requerido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ej: 40x, 63x, 100x'}),
            'espesor_muestra': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ej: 10μm, 50μm'}),
            'tincion_utilizada': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'preparacion_muestra': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'manejo_especial': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tratamiento_previo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'procedencia': forms.TextInput(attrs={'class': 'form-control'}),
            'otro_dato_importante': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'requisitos_finales': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'imagen_muestra': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'croquis': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'tiempo_estimado_numero': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 30}),
            'tiempo_estimado_unidad': forms.Select(attrs={'class': 'form-control'}),
            'becario_asociado': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar becarios asociados solo del usuario actual
        if user:
            self.fields['becario_asociado'].queryset = UsuarioAsociado.objects.filter(
                investigador_principal=user,
                estado='activo'
            )
        else:
            self.fields['becario_asociado'].queryset = UsuarioAsociado.objects.none()
        
        # Hacer el campo de becario opcional
        self.fields['becario_asociado'].required = False
        self.fields['becario_asociado'].empty_label = "Seleccionar becario (opcional)"


class ConfocalMuestraIndividualForm(forms.ModelForm):
    """Formulario para muestras individuales de confocal"""
    
    class Meta:
        model = ConfocalMuestraIndividual
        fields = ['numero_secuencia', 'identificacion', 'descripcion']
        widgets = {
            'numero_secuencia': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'identificacion': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ConfocalAvanceForm(forms.ModelForm):
    """Formulario para avances de solicitudes confocal"""
    
    class Meta:
        model = ConfocalAvance
        fields = ['tipo', 'contenido', 'adjunto', 'visible_para_usuario']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'contenido': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'adjunto': forms.FileInput(attrs={'class': 'form-control'}),
            'visible_para_usuario': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ConfocalDiarioEntradaForm(forms.ModelForm):
    """Formulario para entradas del diario de confocal"""
    
    class Meta:
        model = ConfocalDiarioEntrada
        fields = ['fecha', 'etapa', 'nota']
        widgets = {
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'etapa': forms.Select(attrs={'class': 'form-control'}),
            'nota': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class ConfocalSolicitudModificacionForm(forms.Form):
    """Formulario para solicitar modificaciones a solicitudes confocal"""
    
    TIPO_MODIFICACION_CHOICES = [
        ('numero_muestras', 'Cambiar número de muestras'),
        ('tipo_microscopia', 'Cambiar tipo de microscopía'),
        ('parametros_confocal', 'Modificar parámetros de confocal'),
        ('requisitos_finales', 'Modificar requisitos finales'),
        ('etapas_preparacion', 'Añadir/quitar etapas de preparación'),
        ('observaciones', 'Modificar observaciones'),
        ('otro_dato_importante', 'Modificar otros datos importantes'),
        ('manejo_especial', 'Modificar manejo especial'),
        ('tratamiento_previo', 'Modificar tratamiento previo'),
        ('procedencia', 'Modificar procedencia'),
        ('otro', 'Otra modificación'),
    ]
    
    tipo_modificacion = forms.ChoiceField(
        choices=TIPO_MODIFICACION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Tipo de modificación"
    )
    descripcion_cambio = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label="Descripción del cambio"
    )
    justificacion = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="Justificación"
    )


class ConfocalSolicitudAnulacionForm(forms.Form):
    """Formulario para anular solicitudes confocal"""
    
    justificacion = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label="Justificación de la anulación",
        help_text="Explique por qué desea anular esta solicitud"
    )


class ConfocalIncidenciaForm(forms.Form):
    """Formulario para reportar incidencias en el laboratorio confocal"""
    
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]
    
    CATEGORIA_CHOICES = [
        ('microscopio', 'Microscopio'),
        ('laser', 'Sistema Láser'),
        ('detector', 'Detector'),
        ('software', 'Software'),
        ('infraestructura', 'Infraestructura'),
        ('seguridad', 'Seguridad'),
        ('suministros', 'Suministros'),
        ('comunicaciones', 'Comunicaciones'),
        ('otros', 'Otros'),
    ]
    
    titulo = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Título de la incidencia"
    )
    descripcion = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        label="Descripción detallada"
    )
    categoria = forms.ChoiceField(
        choices=CATEGORIA_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Categoría"
    )
    prioridad = forms.ChoiceField(
        choices=PRIORIDAD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Prioridad"
    )
    ubicacion = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Ubicación"
    )
    equipos_afectados = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Equipos afectados"
    )
    impacto_operaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="Impacto en operaciones"
    )
    acciones_inmediatas = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="Acciones inmediatas"
    )
    archivo_adjunto = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label="Archivo adjunto"
    )


class ConfocalMensajeInternoForm(forms.Form):
    """Formulario para mensajes internos del laboratorio confocal"""
    
    TIPO_MENSAJE_CHOICES = [
        ('consulta', 'Consulta'),
        ('informacion', 'Información'),
        ('recordatorio', 'Recordatorio'),
        ('urgencia', 'Urgencia'),
        ('general', 'General'),
    ]
    
    destinatario = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Destinatario"
    )
    asunto = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Asunto"
    )
    contenido = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        label="Contenido"
    )
    tipo_mensaje = forms.ChoiceField(
        choices=TIPO_MENSAJE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Tipo de mensaje"
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar destinatarios (excluir al usuario actual)
        if user:
            self.fields['destinatario'].queryset = User.objects.exclude(id=user.id)


class MCFSessionCreateForm(forms.ModelForm):
    class Meta:
        model = MCFSession
        fields = ["access_proposal"]
        widgets = {
            "access_proposal": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["access_proposal"].queryset = AccessProposal.objects.filter(
            status="accepted", facility_confocal=True
        ).order_by("-created_at")


class LO3MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class LO3MessageForm(forms.Form):
    body = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        label="Mensaje",
    )
    attachments = forms.FileField(
        required=False,
        widget=LO3MultiFileInput(attrs={"class": "form-control", "multiple": True}),
        label="Adjuntos",
    )


class LO3EquipmentForm(forms.ModelForm):
    class Meta:
        model = LO3Equipment
        fields = [
            "name",
            "manufacturer",
            "model",
            "serial_number",
            "location",
            "status",
            "description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "manufacturer": forms.TextInput(attrs={"class": "form-control"}),
            "model": forms.TextInput(attrs={"class": "form-control"}),
            "serial_number": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class LO3EquipmentDocumentForm(forms.ModelForm):
    class Meta:
        model = LO3EquipmentDocument
        fields = ["title", "doc_type", "file"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "doc_type": forms.Select(attrs={"class": "form-control"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class LO3AttachmentForm(forms.ModelForm):
    class Meta:
        model = LO3Attachment
        fields = ["attachment_type", "description", "file"]
        widgets = {
            "attachment_type": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class LO3CalibrationForm(forms.ModelForm):
    class Meta:
        model = LO3Calibration
        fields = [
            "equipment",
            "performed_at",
            "due_at",
            "performed_by",
            "provider",
            "certificate_file",
            "notes",
        ]
        widgets = {
            "equipment": forms.Select(attrs={"class": "form-control"}),
            "performed_at": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "due_at": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "performed_by": forms.TextInput(attrs={"class": "form-control"}),
            "provider": forms.TextInput(attrs={"class": "form-control"}),
            "certificate_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class LO3ReferenceMaterialForm(forms.ModelForm):
    class Meta:
        model = LO3ReferenceMaterial
        fields = [
            "code",
            "description",
            "catalog_reference",
            "responsible",
            "location",
            "reception_date",
            "expiry_date",
            "observations",
            "status",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "catalog_reference": forms.TextInput(attrs={"class": "form-control"}),
            "responsible": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "reception_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "expiry_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "observations": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }


class LO3ReferenceMaterialDocumentForm(forms.ModelForm):
    class Meta:
        model = LO3ReferenceMaterialDocument
        fields = ["title", "file"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class LO3IncidentForm(forms.ModelForm):
    class Meta:
        model = LO3Incident
        fields = [
            "incident_type",
            "equipment",
            "session",
            "title",
            "description",
            "severity",
            "status",
            "corrective_actions",
        ]
        widgets = {
            "incident_type": forms.Select(attrs={"class": "form-control"}),
            "equipment": forms.Select(attrs={"class": "form-control"}),
            "session": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "severity": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "corrective_actions": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class LO3IncidentAttachmentForm(forms.ModelForm):
    class Meta:
        model = LO3IncidentAttachment
        fields = ["file"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class LO3HabilitationForm(forms.ModelForm):
    class Meta:
        model = LO3Habilitation
        fields = [
            "investigator_user",
            "investigator_full_name",
            "ciemat_id",
            "department_division",
            "center_university",
            "equipment",
            "issued_at",
            "valid_until",
            "linked_technician_account",
        ]
        widgets = {
            "investigator_user": forms.Select(attrs={"class": "form-control"}),
            "investigator_full_name": forms.TextInput(attrs={"class": "form-control"}),
            "ciemat_id": forms.TextInput(attrs={"class": "form-control"}),
            "department_division": forms.TextInput(attrs={"class": "form-control"}),
            "center_university": forms.TextInput(attrs={"class": "form-control"}),
            "equipment": forms.Select(attrs={"class": "form-control"}),
            "issued_at": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "valid_until": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "linked_technician_account": forms.Select(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        investigator_user = cleaned.get("investigator_user")
        investigator_full_name = (cleaned.get("investigator_full_name") or "").strip()
        if not investigator_user and not investigator_full_name:
            self.add_error(
                "investigator_full_name",
                "Indica el nombre del investigador si no seleccionas un usuario.",
            )
        return cleaned


class MCFFinalReportUploadForm(forms.Form):
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


class MCFSampleRecordForm(forms.ModelForm):
    class Meta:
        model = MCFSampleRecord
        fields = [
            "identification",
            "name",
            "details",
            "received_date",
            "analysis_date",
            "return_date",
            "report_delivery_date",
            "operator_name",
            "roughness",
            "image_2d",
            "image_3d",
            "thickness",
            "report_code",
            "observations",
            "indicator_i1",
            "indicator_i2",
        ]
        widgets = {
            "details": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "observations": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "received_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "analysis_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "return_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "report_delivery_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "identification": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "operator_name": forms.TextInput(attrs={"class": "form-control"}),
            "report_code": forms.TextInput(attrs={"class": "form-control"}),
            "indicator_i1": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "indicator_i2": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }

