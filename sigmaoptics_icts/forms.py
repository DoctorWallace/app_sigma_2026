from django import forms

from .models import (
    OpticsAnnualPlan,
    OpticsAnnualPlanEntry,
    OpticsEquipment,
    OpticsEquipmentDocRef,
    OpticsEquipmentIncident,
    OpticsMaintenanceActivity,
    OpticsMaintenanceRecord,
    OpticsReport,
    OpticsSample,
    OpticsSession,
)


class OpticsEquipmentForm(forms.ModelForm):
    class Meta:
        model = OpticsEquipment
        fields = [
            "code",
            "description",
            "is_reference",
            "pattern_type",
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
            "pattern_type": "Tipo de patron",
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


class OpticsEquipmentDocRefForm(forms.ModelForm):
    class Meta:
        model = OpticsEquipmentDocRef
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


class OpticsMaintenanceActivityForm(forms.ModelForm):
    class Meta:
        model = OpticsMaintenanceActivity
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


class OpticsMaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model = OpticsMaintenanceRecord
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


class OpticsEquipmentIncidentForm(forms.ModelForm):
    class Meta:
        model = OpticsEquipmentIncident
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


class OpticsAnnualPlanEntryForm(forms.ModelForm):
    class Meta:
        model = OpticsAnnualPlanEntry
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


class OpticsAnnualPlanYearForm(forms.ModelForm):
    class Meta:
        model = OpticsAnnualPlan
        fields = ["year"]
        labels = {"year": "Ano"}


class OpticsSessionForm(forms.ModelForm):
    class Meta:
        model = OpticsSession
        fields = [
            "request_code",
            "report_code",
            "reception_date",
            "analysis_date",
            "report_delivery_date",
            "measurement_magnitude",
            "procedure_code",
            "status",
        ]
        labels = {
            "request_code": "Codigo solicitud",
            "report_code": "Codigo informe",
            "reception_date": "Fecha recepcion",
            "analysis_date": "Fecha analisis",
            "report_delivery_date": "Fecha informe resultados",
            "measurement_magnitude": "Magnitud medida",
            "procedure_code": "Procedimiento",
            "status": "Estado",
        }


class OpticsSampleForm(forms.ModelForm):
    class Meta:
        model = OpticsSample
        fields = [
            "sequence",
            "identification",
            "name",
            "material",
            "observations",
        ]
        labels = {
            "sequence": "Secuencia",
            "identification": "Referencia muestra",
            "name": "Nombre",
            "material": "Material",
            "observations": "Observaciones",
        }


class OpticsReportForm(forms.ModelForm):
    class Meta:
        model = OpticsReport
        fields = [
            "client_name",
            "project",
            "sample_description",
            "determination",
            "technique",
            "notes",
        ]
        labels = {
            "client_name": "Solicitante",
            "project": "Proyecto",
            "sample_description": "Descripcion de muestras",
            "determination": "Determinacion",
            "technique": "Tecnica",
            "notes": "Notas",
        }
