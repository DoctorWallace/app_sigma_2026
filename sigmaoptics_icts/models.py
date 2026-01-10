from django.conf import settings
from django.db import models, transaction, connection
from django.utils import timezone

from icts.models import AccessProposal


class OpticsEquipment(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_reference = models.BooleanField(default=False, blank=True)
    pattern_type = models.CharField(max_length=50, blank=True)
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


class OpticsEquipmentDocRef(models.Model):
    equipment = models.ForeignKey(
        OpticsEquipment,
        on_delete=models.CASCADE,
        related_name="doc_refs",
    )
    doc_code = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to="sigmaoptics_icts/equipment/docs/",
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


class OpticsMaintenanceActivity(models.Model):
    equipment = models.ForeignKey(
        OpticsEquipment,
        on_delete=models.CASCADE,
        related_name="maintenance_activities",
    )
    activity = models.CharField(max_length=255)
    frequency = models.CharField(max_length=200)
    code = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class OpticsMaintenanceRecord(models.Model):
    equipment = models.ForeignKey(
        OpticsEquipment,
        on_delete=models.CASCADE,
        related_name="maintenance_records",
    )
    performed_at = models.DateField()
    code = models.CharField(max_length=100, blank=True)
    performed_by = models.CharField(max_length=200, blank=True)
    result = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class OpticsEquipmentIncident(models.Model):
    equipment = models.ForeignKey(
        OpticsEquipment,
        on_delete=models.CASCADE,
        related_name="incidents",
    )
    date = models.DateField()
    operation = models.CharField(max_length=255)
    performed_by = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="sigmaoptics_icts/equipment/incidents/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)


class OpticsAnnualPlan(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year"]


class OpticsAnnualPlanEntry(models.Model):
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
        OpticsAnnualPlan,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    equipment = models.ForeignKey(
        OpticsEquipment,
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


class OpticsAnnualPlanChangeLog(models.Model):
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
        OpticsAnnualPlan,
        on_delete=models.CASCADE,
        related_name="change_logs",
    )
    entry = models.ForeignKey(
        OpticsAnnualPlanEntry,
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


class OpticsSession(models.Model):
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
    ]

    access_proposal = models.ForeignKey(
        AccessProposal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="optics_sessions",
    )
    request_code = models.CharField(max_length=16, unique=True, blank=True, db_index=True)
    report_code = models.CharField(max_length=40, unique=True, blank=True, db_index=True)
    reception_date = models.DateField(null=True, blank=True, db_index=True)
    analysis_date = models.DateField(null=True, blank=True, db_index=True)
    report_delivery_date = models.DateField(null=True, blank=True, db_index=True)
    measurement_magnitude = models.CharField(max_length=255, blank=True)
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="optics_sessions",
    )
    procedure_code = models.CharField(max_length=32, default="PT-DTF-07")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    report_pdf = models.FileField(upload_to="sigmaoptics_icts/reports/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.request_code or f"OpticsSession #{self.pk}"

    def _generate_request_code(self):
        year = (self.reception_date or timezone.now().date()).year
        prefix = f"{year}-"
        with transaction.atomic():
            qs = OpticsSession.objects.filter(request_code__startswith=prefix)
            if connection.features.has_select_for_update:
                qs = qs.select_for_update()
            last_code = (
                qs.order_by("-request_code")
                .values_list("request_code", flat=True)
                .first()
            )
            seq = 0
            if last_code:
                try:
                    seq = int(last_code.split("-", 1)[-1])
                except ValueError:
                    seq = 0
            return f"{prefix}{seq + 1:02d}"

    def _generate_report_code(self, request_code):
        if not request_code:
            return ""
        parts = request_code.split("-", 1)
        if len(parts) != 2:
            return f"PT-DTF-07-F03-{request_code}"
        year, seq = parts
        return f"PT-DTF-07-F03-{year}-{seq}"

    def save(self, *args, **kwargs):
        if not self.request_code:
            self.request_code = self._generate_request_code()
        if not self.report_code and self.request_code:
            self.report_code = self._generate_report_code(self.request_code)
        super().save(*args, **kwargs)


class OpticsSample(models.Model):
    session = models.ForeignKey(
        OpticsSession,
        on_delete=models.CASCADE,
        related_name="samples",
    )
    sequence = models.PositiveIntegerField(default=1)
    identification = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255, blank=True)
    observations = models.TextField(blank=True)
    material = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["sequence", "id"]

    def __str__(self):
        return f"Sample {self.sequence} - {self.identification or self.name or self.pk}"


class OpticsReport(models.Model):
    session = models.OneToOneField(
        OpticsSession,
        on_delete=models.CASCADE,
        related_name="report",
    )
    client_name = models.CharField(max_length=255, blank=True)
    project = models.CharField(max_length=255, blank=True)
    sample_description = models.TextField(blank=True)
    determination = models.CharField(max_length=255, blank=True)
    technique = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Optics report {self.session_id}"
