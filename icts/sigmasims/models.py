from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction, connection
from django.utils import timezone

from icts.models import AccessProposal


class SIMSRecord(models.Model):
    access_proposal = models.ForeignKey(
        AccessProposal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sims_records",
    )
    sims_id = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    request_code = models.CharField(max_length=64, blank=True, db_index=True)
    reception_date = models.DateField(db_index=True)
    sample_identification = models.CharField(max_length=255, db_index=True)
    client_name = models.CharField(max_length=255, db_index=True)
    sample_characteristics = models.TextField(blank=True)
    responsible_name = models.CharField(max_length=255, blank=True)
    client_requirements = models.TextField(blank=True)
    analysis_date = models.DateField(null=True, blank=True, db_index=True)
    return_date = models.DateField(null=True, blank=True)
    is_discarded = models.BooleanField(default=False, help_text="La muestra se desecha (no se devuelve al cliente)")
    incidents = models.TextField(blank=True)
    comments = models.TextField(blank=True)
    
    # Campos de análisis (F04 - Control de análisis)
    analysis_responsible = models.CharField(max_length=255, blank=True, help_text="Responsable del análisis")
    ion_gun_optimization = models.TextField(blank=True, help_text="Optimización Cañón Iones (O/Cs, Presión vacío, Intensidad de corriente)")
    acquisition_conditions = models.TextField(blank=True, help_text="Condiciones de la adquisición (en superficie, en profundidad, rango de masas, profundidad, etc.)")
    ion_beam_verification = models.TextField(blank=True, help_text="Verificación condiciones Ihaz de iones (Variación I haz <25%)")
    analysis_observations = models.TextField(blank=True, help_text="Observaciones del análisis")
    report_code = models.CharField(max_length=100, blank=True, help_text="Código del informe (IN-DTF-SIMS-aa-nn)")
    report_delivery_date = models.DateField(null=True, blank=True, help_text="Fecha de entrega del informe")
    
    # Marca si la muestra estaba en la propuesta original
    is_original_sample = models.BooleanField(default=True, help_text="¿La muestra estaba incluida en la propuesta original?")

    # Campos de auditoría para eliminación/cancelación de muestras
    is_removed = models.BooleanField(default=False, help_text="Muestra eliminada/cancelada del estudio")
    removal_reason = models.TextField(blank=True, help_text="Motivo de eliminación (obligatorio si se elimina)")
    removed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sims_records_removed",
        help_text="Usuario que eliminó la muestra"
    )
    removed_at = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora de eliminación")

    class Meta:
        ordering = ["-reception_date", "-id"]

    def __str__(self):
        return f"{self.sims_id or 'SIMS'} - {self.sample_identification}"

    @property
    def quality_i1_days(self):
        if self.analysis_date and self.reception_date:
            return (self.analysis_date - self.reception_date).days
        return None

    @property
    def quality_i1_is_valid(self):
        days = self.quality_i1_days
        return days is not None and days >= 0

    @property
    def i1_days(self):
        return self.quality_i1_days

    def _generate_sims_id(self):
        year = (self.reception_date or timezone.now().date()).year
        prefix = f"SIMS-{year % 100:02d}-"
        with transaction.atomic():
            qs = SIMSRecord.objects.filter(sims_id__startswith=prefix)
            if connection.features.has_select_for_update:
                qs = qs.select_for_update()
            last_id = (
                qs.order_by("-sims_id")
                .values_list("sims_id", flat=True)
                .first()
            )
            seq = 0
            if last_id:
                try:
                    seq = int(last_id.rsplit("-", 1)[-1])
                except ValueError:
                    seq = 0
            return f"{prefix}{seq + 1:03d}"

    def clean(self):
        errors = {}
        if self.analysis_date and self.reception_date:
            if self.analysis_date < self.reception_date:
                errors["analysis_date"] = "La fecha de analisis debe ser posterior a recepcion."
        if self.return_date and self.analysis_date:
            if self.return_date < self.analysis_date:
                errors["return_date"] = "La fecha de devolucion debe ser posterior al analisis."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.sims_id:
            self.sims_id = self._generate_sims_id()
        if not self.request_code and self.access_proposal:
            self.request_code = (self.access_proposal.access_code or "").replace("_", "-")
        self.full_clean()
        super().save(*args, **kwargs)


class SIMSReport(models.Model):
    TECHNIQUE_CHOICES = [
        ("d_sims_positivo_o", "D SIMS positivo con O+"),
        ("d_sims_negativo_cs", "D SIMS negativo con Cs-"),
    ]
    
    access_proposal = models.OneToOneField(
        AccessProposal,
        on_delete=models.CASCADE,
        related_name="sims_report",
    )
    delivery_date = models.DateField(null=True, blank=True, help_text="Fecha de entrega del informe")
    determination = models.CharField(max_length=255, blank=True, help_text="Determinación")
    procedure_used = models.CharField(max_length=64, default="PT-DTF-05", help_text="Procedimiento utilizado")
    technique = models.CharField(
        max_length=50,
        choices=TECHNIQUE_CHOICES,
        blank=True,
        help_text="Técnica utilizada"
    )
    entry_date = models.DateField(null=True, blank=True, help_text="Fecha de entrada (cuando se acepta la propuesta)")
    analysis_date = models.DateField(null=True, blank=True, help_text="Fecha definitiva de análisis")
    technique_text = models.TextField(blank=True)
    sample_description = models.TextField(blank=True)
    measurement_conditions = models.TextField(blank=True)
    results_text = models.TextField(blank=True)
    conclusions = models.TextField(blank=True)

    def __str__(self):
        return f"SIMS Report #{self.access_proposal_id}"

    @property
    def project(self):
        """Proyecto de la propuesta (título o scope)."""
        if self.access_proposal:
            return self.access_proposal.title or self.access_proposal.scope or ""
        return ""

    @property
    def client_identification(self):
        """Identificación del cliente (datos del solicitante)."""
        if not self.access_proposal or not self.access_proposal.applicant:
            return ""
        applicant = self.access_proposal.applicant
        parts = []
        if applicant.get_full_name():
            parts.append(applicant.get_full_name())
        if hasattr(applicant, 'icts_profile') and applicant.icts_profile:
            if applicant.icts_profile.user_siglas:
                parts.append(f"({applicant.icts_profile.user_siglas})")
            if applicant.icts_profile.center:
                parts.append(f"- {applicant.icts_profile.center}")
        if applicant.email:
            parts.append(f"- {applicant.email}")
        return " ".join(parts) if parts else applicant.get_username()

    @property
    def i2_days(self):
        if not self.delivery_date:
            return None
        analysis_date = (
            SIMSRecord.objects.filter(
                access_proposal=self.access_proposal,
                analysis_date__isnull=False,
            )
            .order_by("analysis_date")
            .values_list("analysis_date", flat=True)
            .first()
        )
        if not analysis_date:
            return None
        return (self.delivery_date - analysis_date).days


class SIMSReportImage(models.Model):
    report = models.ForeignKey(
        SIMSReport,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="sigmasims/reports/images/")
    caption = models.CharField(max_length=255, blank=True)


class SIMSReportFile(models.Model):
    report = models.ForeignKey(
        SIMSReport,
        on_delete=models.CASCADE,
        related_name="files",
    )
    file = models.FileField(upload_to="sigmasims/reports/files/")
    caption = models.CharField(max_length=255, blank=True)


class SIMSDocument(models.Model):
    title = models.CharField(max_length=255)
    code = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    date = models.DateField()
    file = models.FileField(upload_to="sigmasims/documents/")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-date", "title"]

    def __str__(self):
        return f"{self.title} ({self.code})"

    def is_pdf(self):
        """Verifica si el archivo es PDF."""
        if not self.file:
            return False
        return self.file.name.lower().endswith('.pdf')

    def get_file_size(self):
        """Obtiene el tamaño del archivo en KB."""
        if not self.file:
            return None
        try:
            size = self.file.size
            return round(size / 1024, 2)  # KB
        except (OSError, AttributeError):
            return None


class SIMSEquipment(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_reference = models.BooleanField(default=False, blank=True)
    responsible = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=255, blank=True)
    received_date = models.DateField(null=True, blank=True)
    decommission_date = models.DateField(null=True, blank=True)
    observations = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    brand = models.CharField(max_length=200, blank=True)
    model = models.CharField(max_length=200, blank=True)
    serial_number = models.CharField(max_length=200, blank=True)
    supplier = models.CharField(max_length=200, blank=True)
    inventory_number = models.CharField(max_length=200, blank=True)
    measurement_magnitude = models.CharField(max_length=200, blank=True)
    measurement_range = models.CharField(max_length=200, blank=True)
    breakdown_contact = models.TextField(blank=True)
    calibration_acceptance_criteria = models.TextField(blank=True)
    specification_conformity = models.TextField(blank=True)
    associated_equipment = models.TextField(blank=True)
    technical_characteristics = models.TextField(blank=True)
    usage_instructions = models.TextField(blank=True)
    validation_data = models.TextField(blank=True)
    maintenance_required = models.BooleanField(default=False, blank=True)
    maintenance_company = models.CharField(max_length=200, blank=True)
    maintenance_procedure = models.CharField(max_length=200, blank=True)
    maintenance_period = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class SIMSEquipmentDocRef(models.Model):
    equipment = models.ForeignKey(
        SIMSEquipment,
        on_delete=models.CASCADE,
        related_name="doc_refs",
    )
    doc_code = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to="sigmasims/equipment/docs/",
        null=True,
        blank=True,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)


class SIMSMaintenanceActivity(models.Model):
    equipment = models.ForeignKey(
        SIMSEquipment,
        on_delete=models.CASCADE,
        related_name="maintenance_activities",
    )
    activity = models.CharField(max_length=255)
    frequency = models.CharField(max_length=200)
    code = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SIMSMaintenanceRecord(models.Model):
    equipment = models.ForeignKey(
        SIMSEquipment,
        on_delete=models.CASCADE,
        related_name="maintenance_records",
    )
    performed_at = models.DateField()
    code = models.CharField(max_length=100, blank=True)
    performed_by = models.CharField(max_length=200, blank=True)
    result = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SIMSEquipmentIncident(models.Model):
    equipment = models.ForeignKey(
        SIMSEquipment,
        on_delete=models.CASCADE,
        related_name="incidents",
    )
    date = models.DateField()
    operation = models.CharField(max_length=255)
    performed_by = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="sigmasims/equipment/incidents/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)


class SIMSSparePartInventory(models.Model):
    item_name = models.CharField(max_length=255)
    stock_2024_01 = models.IntegerField(null=True, blank=True)
    stock_2024_06 = models.IntegerField(null=True, blank=True)
    next_orders = models.IntegerField(null=True, blank=True)
    actions = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["item_name"]


class SIMSAnnualPlan(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year"]


class SIMSAnnualPlanEntry(models.Model):
    ACTIVITY_MAINTENANCE = "MAINTENANCE"
    ACTIVITY_CALIBRATION = "CALIBRATION"
    ACTIVITY_VERIFICATION = "VERIFICATION"
    ACTIVITY_VALIDATION = "VALIDATION"
    ACTIVITY_CONTROL = "CONTROL"
    ACTIVITY_CHOICES = [
        (ACTIVITY_MAINTENANCE, "Mantenimiento"),
        (ACTIVITY_CALIBRATION, "Calibracion"),
        (ACTIVITY_VERIFICATION, "Verificacion"),
        (ACTIVITY_VALIDATION, "Validacion"),
        (ACTIVITY_CONTROL, "Control"),
    ]

    EXECUTION_INTERNAL = "INTERNAL"
    EXECUTION_EXTERNAL = "EXTERNAL"
    EXECUTION_CHOICES = [
        (EXECUTION_INTERNAL, "INTERNO"),
        (EXECUTION_EXTERNAL, "EXTERNO"),
    ]

    plan = models.ForeignKey(
        SIMSAnnualPlan,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    equipment = models.ForeignKey(
        SIMSEquipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    equipment_code = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=255, blank=True)
    activity = models.CharField(max_length=30, choices=ACTIVITY_CHOICES)
    execution_type = models.CharField(max_length=10, choices=EXECUTION_CHOICES)
    month_01 = models.BooleanField(default=False)
    month_02 = models.BooleanField(default=False)
    month_03 = models.BooleanField(default=False)
    month_04 = models.BooleanField(default=False)
    month_05 = models.BooleanField(default=False)
    month_06 = models.BooleanField(default=False)
    month_07 = models.BooleanField(default=False)
    month_08 = models.BooleanField(default=False)
    month_09 = models.BooleanField(default=False)
    month_10 = models.BooleanField(default=False)
    month_11 = models.BooleanField(default=False)
    month_12 = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["plan__year", "equipment_code", "activity"]

    def save(self, *args, **kwargs):
        if self.equipment and not self.equipment_code:
            self.equipment_code = self.equipment.code
        super().save(*args, **kwargs)


class SIMSAnnualPlanChangeLog(models.Model):
    ACTION_COPY = "COPY"
    ACTION_CREATE = "CREATE"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"
    ACTION_CHOICES = [
        (ACTION_COPY, "Copia"),
        (ACTION_CREATE, "Creacion"),
        (ACTION_UPDATE, "Actualizacion"),
        (ACTION_DELETE, "Borrado"),
    ]

    plan = models.ForeignKey(
        SIMSAnnualPlan,
        on_delete=models.CASCADE,
        related_name="change_logs",
    )
    entry = models.ForeignKey(
        SIMSAnnualPlanEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    before_data = models.JSONField(null=True, blank=True)
    after_data = models.JSONField(null=True, blank=True)
    message = models.CharField(max_length=255, blank=True)


class SIMSReferenceMaterial(models.Model):
    """Material de referencia SIMS."""
    # Información básica
    code = models.CharField(max_length=100, unique=True, db_index=True, help_text="Código del material de referencia")
    is_pattern = models.BooleanField(default=False, help_text="¿Es patrón?")
    PATTERN_TYPE_CHOICES = [
        ("", "---------"),
        ("Primario", "Primario"),
        ("Secundario", "Secundario"),
        ("De trabajo", "De trabajo"),
    ]
    pattern_type = models.CharField(
        max_length=50, 
        blank=True, 
        choices=PATTERN_TYPE_CHOICES,
        help_text="Tipo de patrón"
    )
    responsible = models.CharField(max_length=100, blank=True, help_text="Responsable del material")
    description = models.TextField(blank=True, help_text="Descripción del material")
    reference = models.CharField(max_length=255, blank=True, help_text="Referencia (inventario, etc.)")
    reception_date = models.DateField(null=True, blank=True, help_text="Fecha de recepción")
    supplier = models.CharField(max_length=255, blank=True, help_text="Proveedor")
    location = models.TextField(blank=True, help_text="Localización")
    conservation_conditions = models.TextField(blank=True, help_text="Condiciones de conservación")
    
    # Propiedades radiactivas (si aplica)
    emission_type = models.CharField(max_length=100, blank=True, help_text="Tipo de emisión")
    activity = models.CharField(max_length=100, blank=True, help_text="Actividad")
    emission_rate = models.CharField(max_length=100, blank=True, help_text="Tasa de emisión")
    expiry_date = models.DateField(null=True, blank=True, help_text="Caducidad")
    opening_date = models.DateField(null=True, blank=True, help_text="Fecha apertura (en caso líquidos)")
    
    # Calibración
    calibration_acceptance_criteria = models.TextField(blank=True, help_text="Criterio de aceptación calibraciones")
    conformity_verification = models.TextField(blank=True, help_text="Verificación de la conformidad del MR con la especificación")
    
    # Propiedades físicas
    physical_properties = models.TextField(blank=True, help_text="Propiedades físicas")
    
    # Documentación
    associated_documentation = models.TextField(blank=True, help_text="Documentación asociada (Manual de instrucciones, Procedimientos, etc.)")
    
    # Instrucciones
    technical_usage_instructions = models.TextField(blank=True, help_text="Instrucciones técnicas de uso")
    
    # Incidencias
    detected_incidents = models.TextField(blank=True, help_text="Incidencias detectadas")
    
    # Metadatos
    is_active = models.BooleanField(default=True, help_text="Material activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Cache de datos del Excel (para compatibilidad)
    excel_data = models.JSONField(null=True, blank=True, help_text="Datos completos leídos del Excel (cache)")
    
    class Meta:
        ordering = ["code"]
        verbose_name = "Material de Referencia SIMS"
        verbose_name_plural = "Materiales de Referencia SIMS"

    def __str__(self):
        return f"{self.code} - {self.description[:50] if self.description else 'Sin descripción'}"
    
    def get_filled_fields(self):
        """Retorna un diccionario con solo los campos que tienen datos."""
        fields_map = {
            "Código": self.code,
            "Patrón": "Sí" if self.is_pattern else None,
            "Tipo de patrón": self.pattern_type if self.pattern_type else None,
            "Responsable": self.responsible if self.responsible else None,
            "Descripción": self.description if self.description else None,
            "Referencia": self.reference if self.reference else None,
            "Fecha recepción": self.reception_date.strftime("%Y-%m-%d") if self.reception_date else None,
            "Proveedor": self.supplier if self.supplier else None,
            "Localización": self.location if self.location else None,
            "Condiciones conservación": self.conservation_conditions if self.conservation_conditions else None,
            "Tipo emisión": self.emission_type if self.emission_type else None,
            "Actividad": self.activity if self.activity else None,
            "Tasa emisión": self.emission_rate if self.emission_rate else None,
            "Caducidad": self.expiry_date.strftime("%Y-%m-%d") if self.expiry_date else None,
            "Fecha apertura": self.opening_date.strftime("%Y-%m-%d") if self.opening_date else None,
            "Criterio de aceptación calibraciones": self.calibration_acceptance_criteria if self.calibration_acceptance_criteria else None,
            "Verificación de la conformidad": self.conformity_verification if self.conformity_verification else None,
            "Propiedades físicas": self.physical_properties if self.physical_properties else None,
            "Documentación asociada": self.associated_documentation if self.associated_documentation else None,
            "Instrucciones técnicas de uso": self.technical_usage_instructions if self.technical_usage_instructions else None,
            "Incidencias detectadas": self.detected_incidents if self.detected_incidents else None,
        }
        # Filtrar campos vacíos o None
        return {k: v for k, v in fields_map.items() if v is not None and str(v).strip()}
