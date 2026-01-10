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
)


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
        labels = {
            "access_proposal": "Propuesta asociada",
            "request_code": "Número de solicitud",
            "reception_date": "Fecha de recepción",
            "sample_identification": "Identificación muestra",
            "client_name": "Cliente",
            "sample_characteristics": "Características de la muestra",
            "responsible_name": "Responsable",
            "client_requirements": "Requerimientos cliente",
            "analysis_date": "Fecha del análisis",
            "return_date": "Fecha de devolución",
            "incidents": "Observaciones e incidencias",
            "comments": "Comentarios",
        }
        help_texts = {
            "access_proposal": "Vincula el registro con una propuesta SIMS, si aplica.",
            "request_code": "Código de solicitud/propuesta tal como aparece en el Excel.",
            "reception_date": "Fecha de recepción de la muestra.",
            "analysis_date": "Fecha en la que se realizó el análisis.",
            "return_date": "Fecha de devolución de la muestra.",
            "incidents": "Observaciones e incidencias relevantes.",
        }


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
