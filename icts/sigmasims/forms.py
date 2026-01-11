from django import forms

from .models import (
    SIMSAnnualPlan,
    SIMSAnnualPlanEntry,
    SIMSDocument,
    SIMSEquipment,
    SIMSEquipmentDocRef,
    SIMSEquipmentIncident,
    SIMSMaintenanceActivity,
    SIMSMaintenanceRecord,
    SIMSRecord,
    SIMSReport,
    SIMSSparePartInventory,
    SIMSReferenceMaterial,
)


class SIMSRecordForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        technicians_list = kwargs.pop("technicians_list", None)
        super().__init__(*args, **kwargs)
        if technicians_list:
            self.fields["responsible_name"].widget = forms.Select(
                choices=[("", "---------")] + [(tech["siglas"] or tech["username"], tech["display"]) for tech in technicians_list],
                attrs={"class": "form-control"}
            )
    
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
            "is_discarded",
            # Campos de análisis
            "analysis_responsible",
            "ion_gun_optimization",
            "acquisition_conditions",
            "ion_beam_verification",
            "analysis_observations",
            "report_code",
            "report_delivery_date",
            "is_original_sample",
        ]
        labels = {
            "access_proposal": "Propuesta asociada",
            "request_code": "Número de solicitud",
            "reception_date": "Fecha de recepción",
            "sample_identification": "Identificación muestra",
            "client_name": "Cliente",
            "sample_characteristics": "Características de la muestra",
            "responsible_name": "Responsable recepción",
            "client_requirements": "Requerimientos cliente",
            "analysis_date": "Fecha del análisis",
            "return_date": "Fecha de devolución",
            "is_discarded": "Se desecha la muestra",
            "incidents": "Observaciones e incidencias",
            "comments": "Comentarios",
            # Campos de análisis
            "analysis_responsible": "Responsable del análisis",
            "ion_gun_optimization": "Optimización Cañón Iones",
            "acquisition_conditions": "Condiciones de la adquisición",
            "ion_beam_verification": "Verificación condiciones Ihaz de iones",
            "analysis_observations": "Observaciones del análisis",
            "report_code": "Código del informe (IN-DTF-SIMS-aa-nn)",
            "report_delivery_date": "Fecha de entrega del informe",
            "is_original_sample": "Muestra incluida en propuesta original",
            "is_discarded": "Se desecha la muestra",
        }
        help_texts = {
            "access_proposal": "Vincula el registro con una propuesta SIMS, si aplica.",
            "request_code": "Código de solicitud/propuesta tal como aparece en el Excel.",
            "reception_date": "Fecha de recepción de la muestra.",
            "analysis_date": "Fecha en la que se realizó el análisis.",
            "return_date": "Fecha de devolución de la muestra.",
            "incidents": "Observaciones e incidencias relevantes.",
            "is_original_sample": "Desmarcar si la muestra no estaba incluida en la propuesta original.",
            "is_discarded": "Marcar si la muestra se desecha (no se devuelve al cliente). Si no se indica nada, se desecha automáticamente a los 2 meses.",
        }
        widgets = {
            "reception_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "analysis_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "return_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "report_delivery_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "is_discarded": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sample_characteristics": forms.Textarea(attrs={"rows": 3}),
            "client_requirements": forms.Textarea(attrs={"rows": 3}),
            "incidents": forms.Textarea(attrs={"rows": 3}),
            "comments": forms.Textarea(attrs={"rows": 3}),
            "ion_gun_optimization": forms.Textarea(attrs={"rows": 2}),
            "acquisition_conditions": forms.Textarea(attrs={"rows": 3}),
            "ion_beam_verification": forms.Textarea(attrs={"rows": 2}),
            "analysis_observations": forms.Textarea(attrs={"rows": 3}),
            "is_original_sample": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        help_texts = {
            "access_proposal": "Vincula el registro con una propuesta SIMS, si aplica.",
            "request_code": "Código de solicitud/propuesta tal como aparece en el Excel.",
            "reception_date": "Fecha de recepción de la muestra.",
            "analysis_date": "Fecha en la que se realizó el análisis.",
            "return_date": "Fecha de devolución de la muestra.",
            "incidents": "Observaciones e incidencias relevantes.",
            "is_original_sample": "Desmarcar si la muestra no estaba incluida en la propuesta original.",
        }


class SIMSReportForm(forms.ModelForm):
    class Meta:
        model = SIMSReport
        fields = [
            "delivery_date",
            "determination",
            "procedure_used",
            "technique",
            "entry_date",
            "analysis_date",
            "technique_text",
            "sample_description",
            "measurement_conditions",
            "results_text",
            "conclusions",
        ]
        labels = {
            "delivery_date": "Fecha de entrega",
            "determination": "Determinación",
            "procedure_used": "Procedimiento",
            "technique": "Técnica",
            "entry_date": "Fecha de entrada",
            "analysis_date": "Fecha de análisis",
            "technique_text": "Texto de técnica",
            "sample_description": "Descripción de muestras",
            "measurement_conditions": "Condiciones de medida",
            "results_text": "Resultados",
            "conclusions": "Conclusiones",
        }
        widgets = {
            "delivery_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "entry_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "analysis_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "determination": forms.TextInput(attrs={"class": "form-control"}),
            "procedure_used": forms.TextInput(attrs={"class": "form-control"}),
            "technique": forms.Select(attrs={"class": "form-control"}),
            "technique_text": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "sample_description": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "measurement_conditions": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "results_text": forms.Textarea(attrs={"rows": 6, "class": "form-control"}),
            "conclusions": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
        }
        help_texts = {
            "delivery_date": "Fecha de entrega del informe al cliente",
            "entry_date": "Fecha cuando se acepta la propuesta (pasa de disponible a aceptada)",
            "analysis_date": "Fecha definitiva de análisis",
            "technique": "Seleccione la técnica utilizada",
        }


class SIMSDocumentForm(forms.ModelForm):
    class Meta:
        model = SIMSDocument
        fields = [
            "title",
            "code",
            "version",
            "date",
            "file",
        ]
        widgets = {
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control",
            }),
            "file": forms.FileInput(attrs={
                "accept": ".pdf",
                "class": "form-control",
            }),
        }
        help_texts = {
            "file": "Solo se permiten archivos PDF.",
            "date": "Seleccione la fecha del documento.",
        }

    def clean_file(self):
        """Validar que el archivo sea PDF."""
        file = self.cleaned_data.get("file")
        if file:
            # Validar extensión
            if not file.name.lower().endswith('.pdf'):
                raise forms.ValidationError(
                    "Solo se permiten archivos PDF. Por favor, suba un archivo con extensión .pdf"
                )
            # Validar tipo MIME (opcional, pero más seguro)
            if hasattr(file, 'content_type'):
                if file.content_type not in ['application/pdf', 'application/x-pdf']:
                    raise forms.ValidationError(
                        "El archivo no es un PDF válido. Por favor, suba un archivo PDF."
                    )
        return file

    def save(self, commit=True):
        """Asegurar que is_active siempre sea True al crear."""
        instance = super().save(commit=False)
        instance.is_active = True  # Siempre activo al crear/editar
        if commit:
            instance.save()
        return instance


class SIMSEquipmentForm(forms.ModelForm):
    class Meta:
        model = SIMSEquipment
        fields = [
            "code",
            "description",
            "is_reference",
            "brand",
            "model",
            "serial_number",
            "supplier",
            "inventory_number",
            "responsible",
            "location",
            "received_date",
            "decommission_date",
            "observations",
            "measurement_magnitude",
            "measurement_range",
            "breakdown_contact",
            "calibration_acceptance_criteria",
            "specification_conformity",
            "associated_equipment",
            "technical_characteristics",
            "usage_instructions",
            "validation_data",
            "maintenance_required",
            "maintenance_company",
            "maintenance_procedure",
            "maintenance_period",
        ]
        labels = {
            "code": "Codigo",
            "description": "Descripcion",
            "is_reference": "Es patron?",
            "brand": "Marca",
            "model": "Modelo",
            "serial_number": "Nro serie",
            "supplier": "Proveedor",
            "inventory_number": "Nro inventario",
            "responsible": "Responsable",
            "location": "Localizacion",
            "received_date": "Fecha recepcion",
            "decommission_date": "Fecha baja",
            "observations": "Observaciones",
            "measurement_magnitude": "Magnitud de medida",
            "measurement_range": "Rango de medida",
            "breakdown_contact": "Empresa averias, contacto y telefono",
            "calibration_acceptance_criteria": "Criterio de aceptacion calibraciones",
            "specification_conformity": "Verificacion conformidad con la especificacion",
            "associated_equipment": "Equipos asociados",
            "technical_characteristics": "Caracteristicas tecnicas",
            "usage_instructions": "Instrucciones tecnicas de uso",
            "validation_data": "Datos de validacion",
            "maintenance_required": "Es necesaria la realizacion?",
            "maintenance_company": "Empresa encargada",
            "maintenance_procedure": "Procedimiento",
            "maintenance_period": "Periodo entre mantenimiento",
        }


class SIMSEquipmentDocRefForm(forms.ModelForm):
    class Meta:
        model = SIMSEquipmentDocRef
        fields = [
            "doc_code",
            "title",
            "file",
        ]
        labels = {
            "doc_code": "Codigo del documento",
            "title": "Titulo",
            "file": "Archivo",
        }


class SIMSMaintenanceActivityForm(forms.ModelForm):
    class Meta:
        model = SIMSMaintenanceActivity
        fields = [
            "activity",
            "frequency",
            "code",
        ]
        labels = {
            "activity": "Actividad",
            "frequency": "Frecuencia",
            "code": "Codigo",
        }


class SIMSMaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model = SIMSMaintenanceRecord
        fields = [
            "performed_at",
            "code",
            "performed_by",
            "result",
            "notes",
        ]
        labels = {
            "performed_at": "Fecha",
            "code": "Codigo",
            "performed_by": "Realizado por",
            "result": "Resultado",
            "notes": "Notas",
        }


class SIMSEquipmentIncidentForm(forms.ModelForm):
    class Meta:
        model = SIMSEquipmentIncident
        fields = [
            "date",
            "operation",
            "performed_by",
            "description",
            "attachment",
        ]
        labels = {
            "date": "Fecha",
            "operation": "Operacion",
            "performed_by": "Realizada por",
            "description": "Descripcion",
            "attachment": "Adjunto",
        }


class SIMSSparePartInventoryForm(forms.ModelForm):
    class Meta:
        model = SIMSSparePartInventory
        fields = [
            "item_name",
            "stock_2024_01",
            "stock_2024_06",
            "next_orders",
            "actions",
        ]
        labels = {
            "item_name": "Nombre del repuesto",
            "stock_2024_01": "Cantidad en stock a 01/24",
            "stock_2024_06": "Cantidad en stock a 06/2024",
            "next_orders": "Proximos pedidos",
            "actions": "Acciones",
        }


class SIMSAnnualPlanEntryForm(forms.ModelForm):
    class Meta:
        model = SIMSAnnualPlanEntry
        fields = [
            "equipment",
            "equipment_code",
            "description",
            "activity",
            "execution_type",
            "month_01",
            "month_02",
            "month_03",
            "month_04",
            "month_05",
            "month_06",
            "month_07",
            "month_08",
            "month_09",
            "month_10",
            "month_11",
            "month_12",
            "notes",
        ]
        labels = {
            "equipment": "Equipo",
            "equipment_code": "Codigo equipo",
            "description": "Descripcion",
            "activity": "Actividad",
            "execution_type": "Tipo ejecucion",
            "month_01": "E",
            "month_02": "F",
            "month_03": "M",
            "month_04": "A",
            "month_05": "M",
            "month_06": "J",
            "month_07": "J",
            "month_08": "A",
            "month_09": "S",
            "month_10": "O",
            "month_11": "N",
            "month_12": "D",
            "notes": "Notas",
        }
        widgets = {
            "month_01": forms.CheckboxInput(),
            "month_02": forms.CheckboxInput(),
            "month_03": forms.CheckboxInput(),
            "month_04": forms.CheckboxInput(),
            "month_05": forms.CheckboxInput(),
            "month_06": forms.CheckboxInput(),
            "month_07": forms.CheckboxInput(),
            "month_08": forms.CheckboxInput(),
            "month_09": forms.CheckboxInput(),
            "month_10": forms.CheckboxInput(),
            "month_11": forms.CheckboxInput(),
            "month_12": forms.CheckboxInput(),
        }


class SIMSAnnualPlanYearForm(forms.ModelForm):
    class Meta:
        model = SIMSAnnualPlan
        fields = ["year"]
        labels = {"year": "Ano"}


class SIMSReferenceMaterialForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si es edición, hacer el código readonly
        if self.instance and self.instance.pk:
            self.fields['code'].widget.attrs['readonly'] = True
            self.fields['code'].widget.attrs['style'] = 'background-color: #f3f4f6; cursor: not-allowed;'
    
    class Meta:
        model = SIMSReferenceMaterial
        fields = [
            "code",
            "is_pattern",
            "pattern_type",
            "responsible",
            "description",
            "reference",
            "reception_date",
            "supplier",
            "location",
            "conservation_conditions",
            "emission_type",
            "activity",
            "emission_rate",
            "expiry_date",
            "opening_date",
            "calibration_acceptance_criteria",
            "conformity_verification",
            "physical_properties",
            "associated_documentation",
            "technical_usage_instructions",
            "detected_incidents",
            "is_active",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "is_pattern": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "pattern_type": forms.Select(attrs={"class": "form-control"}),
            "responsible": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "reference": forms.TextInput(attrs={"class": "form-control"}),
            "reception_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "supplier": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "conservation_conditions": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "emission_type": forms.TextInput(attrs={"class": "form-control"}),
            "activity": forms.TextInput(attrs={"class": "form-control"}),
            "emission_rate": forms.TextInput(attrs={"class": "form-control"}),
            "expiry_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "opening_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "calibration_acceptance_criteria": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "conformity_verification": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "physical_properties": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "associated_documentation": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "technical_usage_instructions": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "detected_incidents": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "code": "Código",
            "is_pattern": "¿Es patrón?",
            "pattern_type": "Tipo de patrón",
            "responsible": "Responsable",
            "description": "Descripción",
            "reference": "Referencia",
            "reception_date": "Fecha recepción",
            "supplier": "Proveedor",
            "location": "Localización",
            "conservation_conditions": "Condiciones conservación",
            "emission_type": "Tipo emisión",
            "activity": "Actividad",
            "emission_rate": "Tasa emisión",
            "expiry_date": "Caducidad",
            "opening_date": "Fecha apertura (en caso líquidos)",
            "calibration_acceptance_criteria": "Criterio de aceptación calibraciones",
            "conformity_verification": "Verificación de la conformidad del MR con la especificación",
            "physical_properties": "Propiedades físicas",
            "associated_documentation": "Documentación asociada (Manual de instrucciones, Procedimientos, etc.)",
            "technical_usage_instructions": "Instrucciones técnicas de uso",
            "detected_incidents": "Incidencias detectadas",
            "is_active": "Activo",
        }
        help_texts = {
            "code": "Código único del material de referencia (ej: MR-DTF-L05-01)",
            "reception_date": "Fecha en que se recibió el material",
            "expiry_date": "Fecha de caducidad si aplica",
        }


class SIMSRecordRemovalForm(forms.Form):
    """Formulario para eliminar/cancelar una muestra con motivo obligatorio."""
    removal_reason = forms.CharField(
        label="Motivo de eliminación",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Indique el motivo por el cual se elimina esta muestra (obligatorio)"
        }),
        required=True,
        help_text="Este campo es obligatorio. Explique por qué se elimina la muestra del estudio."
    )
    
    def clean_removal_reason(self):
        reason = self.cleaned_data.get("removal_reason", "").strip()
        if len(reason) < 10:
            raise forms.ValidationError("El motivo debe tener al menos 10 caracteres.")
        return reason
