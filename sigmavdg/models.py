from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from icts.models import AccessProposal


class VDGYearCounter(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    counter = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["year"]
        verbose_name = "VDG year counter"
        verbose_name_plural = "VDG year counters"

    def __str__(self):
        return f"{self.year}: {self.counter}"

    @classmethod
    def next_counter(cls, year):
        with transaction.atomic():
            counter_obj, _ = cls.objects.select_for_update().get_or_create(
                year=year, defaults={"counter": 0}
            )
            counter_obj.counter += 1
            counter_obj.save(update_fields=["counter"])
            return counter_obj.counter


class VDGSession(models.Model):
    STATUS_CHOICES = (
        ("in_progress", "In progress"),
        ("completed", "Completed"),
    )

    access_proposal = models.ForeignKey(
        AccessProposal, on_delete=models.CASCADE, related_name="vdg_sessions"
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="vdg_sessions"
    )
    lot_code = models.CharField(max_length=20, unique=True)
    report_code = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    irradiation_start_date = models.DateField(null=True, blank=True)
    irradiation_end_date = models.DateField(null=True, blank=True)
    report_issue_date = models.DateField(null=True, blank=True)
    report_delivery_date = models.DateField(null=True, blank=True)
    notice_pdf = models.FileField(upload_to="vdg/notices/", null=True, blank=True)
    report_pdf = models.FileField(upload_to="vdg/reports/", null=True, blank=True)
    request_snapshot = models.JSONField(default=dict, blank=True)
    observations = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "VDG session"
        verbose_name_plural = "VDG sessions"

    def __str__(self):
        return f"{self.lot_code} - {self.access_proposal.title}"

    def _assign_codes(self):
        year_full = timezone.now().year
        counter = VDGYearCounter.next_counter(year_full)
        year_short = year_full % 100
        lot_code = f"VDG-{year_short:02d}-{counter:03d}"
        report_code = f"IN-DTF-VDG-{year_full}-{counter:03d}"
        return lot_code, report_code

    def _derive_report_code(self):
        if not self.lot_code:
            return ""
        parts = self.lot_code.split("-")
        if len(parts) != 3:
            return f"IN-DTF-{self.lot_code}"
        _, year_short, counter = parts
        try:
            year_short_int = int(year_short)
            counter_int = int(counter)
        except ValueError:
            return f"IN-DTF-{self.lot_code}"
        year_full = (timezone.now().year // 100) * 100 + year_short_int
        return f"IN-DTF-VDG-{year_full}-{counter_int:03d}"

    def save(self, *args, **kwargs):
        if not self.request_snapshot and self.access_proposal_id:
            payload = self.access_proposal.facility_data or {}
            if isinstance(payload, dict):
                self.request_snapshot = payload.get("vdg", {}) or {}
        if not self.lot_code:
            with transaction.atomic():
                self.lot_code, self.report_code = self._assign_codes()
        elif not self.report_code:
            self.report_code = self._derive_report_code()
        super().save(*args, **kwargs)


class VDGSampleRecord(models.Model):
    SOURCE_CHOICES = (
        ("proposal", "Proposal"),
        ("session", "Session"),
    )

    session = models.ForeignKey(
        VDGSession, on_delete=models.CASCADE, related_name="samples"
    )
    sequence = models.PositiveIntegerField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="proposal")
    code = models.CharField(max_length=200, blank=True)
    material = models.CharField(max_length=200, blank=True)
    electron_fluence = models.CharField(max_length=200, blank=True)
    temperature = models.CharField(max_length=200, blank=True)
    atmosphere = models.CharField(max_length=200, blank=True)
    sample_size = models.CharField(max_length=200, blank=True)
    sample_geometry = models.CharField(max_length=200, blank=True)
    fluence_result = models.CharField(max_length=200, blank=True)
    current_na = models.CharField(max_length=100, blank=True)
    time_minutes = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["sequence"]
        unique_together = [("session", "sequence")]
        verbose_name = "VDG sample record"
        verbose_name_plural = "VDG sample records"

    def __str__(self):
        return f"{self.session.lot_code} #{self.sequence} - {self.code or '-'}"


class VDGEquipment(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_reference = models.BooleanField(default=False)
    responsible = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    received_date = models.DateField(null=True, blank=True)
    decommission_date = models.DateField(null=True, blank=True)
    observations = models.TextField(blank=True)
    brand = models.CharField(max_length=200, blank=True)
    model = models.CharField(max_length=200, blank=True)
    serial_number = models.CharField(max_length=200, blank=True)
    range = models.CharField(max_length=200, blank=True)
    resolution = models.CharField(max_length=200, blank=True)
    tolerance = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "VDG equipment"
        verbose_name_plural = "VDG equipment"

    def __str__(self):
        return self.code


class VDGEquipmentDocument(models.Model):
    DOC_TYPE_CHOICES = (
        ("certificate", "Certificado"),
        ("calibration", "Calibracion"),
        ("maintenance", "Mantenimiento"),
        ("other", "Otro"),
    )

    equipment = models.ForeignKey(
        VDGEquipment, on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, default="other")
    file = models.FileField(upload_to="vdg/equipment/")
    date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="vdg_equipment_documents",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "VDG equipment document"
        verbose_name_plural = "VDG equipment documents"

    def __str__(self):
        return self.file.name.rsplit("/", 1)[-1]


class VDGEquipmentIncident(models.Model):
    SEVERITY_CHOICES = (
        ("low", "Baja"),
        ("medium", "Media"),
        ("high", "Alta"),
    )
    STATUS_CHOICES = (
        ("open", "Abierta"),
        ("in_progress", "En curso"),
        ("closed", "Cerrada"),
    )

    equipment = models.ForeignKey(
        VDGEquipment, on_delete=models.CASCADE, related_name="incidents"
    )
    date = models.DateField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="low")
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    attachment = models.FileField(upload_to="vdg/incidents/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "VDG equipment incident"
        verbose_name_plural = "VDG equipment incidents"

    def __str__(self):
        return f"{self.equipment.code} - {self.date:%Y-%m-%d}"


class VDGItem(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "VDG item"
        verbose_name_plural = "VDG items"

    def __str__(self):
        return self.code


class VDGItemMovement(models.Model):
    RECEIPT_STATUS_CHOICES = (
        ("ok", "Ok"),
        ("damaged", "Danado"),
        ("not_received", "No recibido"),
        ("other", "Otro"),
    )

    item = models.ForeignKey(
        VDGItem, on_delete=models.CASCADE, related_name="movements"
    )
    fecha_salida = models.DateField()
    motivo_salida = models.CharField(max_length=200)
    forma_envio = models.CharField(max_length=200, blank=True)
    destino = models.CharField(max_length=200, blank=True)
    responsable_destino = models.CharField(max_length=200, blank=True)
    cumplimentado_por_salida = models.CharField(max_length=200, blank=True)
    fecha_entrada = models.DateField(null=True, blank=True)
    estado_recepcion = models.CharField(
        max_length=20, choices=RECEIPT_STATUS_CHOICES, blank=True
    )
    estado_recepcion_detalle = models.CharField(max_length=200, blank=True)
    cumplimentado_por_entrada = models.CharField(max_length=200, blank=True)
    notas = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha_salida"]
        verbose_name = "VDG item movement"
        verbose_name_plural = "VDG item movements"

    def __str__(self):
        return f"{self.item.code} - {self.fecha_salida:%Y-%m-%d}"
