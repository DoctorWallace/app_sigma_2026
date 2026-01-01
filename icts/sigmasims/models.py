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
    sample_characteristics = models.TextField()
    responsible_name = models.CharField(max_length=255)
    client_requirements = models.TextField()
    analysis_date = models.DateField(null=True, blank=True, db_index=True)
    return_date = models.DateField(null=True, blank=True)
    incidents = models.TextField(blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ["-reception_date", "-id"]

    def __str__(self):
        return f"{self.sims_id or 'SIMS'} - {self.sample_identification}"

    @property
    def i1_days(self):
        if self.analysis_date and self.reception_date:
            return (self.analysis_date - self.reception_date).days
        return None

    def _generate_sims_id(self):
        year = (self.reception_date or timezone.now().date()).year
        prefix = f"SIMS_{year % 100:02d}_"
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
                    seq = int(last_id.rsplit("_", 1)[-1])
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
            self.request_code = self.access_proposal.access_code or ""
        self.full_clean()
        super().save(*args, **kwargs)


class SIMSReport(models.Model):
    access_proposal = models.OneToOneField(
        AccessProposal,
        on_delete=models.CASCADE,
        related_name="sims_report",
    )
    delivery_date = models.DateField(null=True, blank=True)
    determination = models.CharField(max_length=255, blank=True)
    procedure_used = models.CharField(max_length=64, default="PT-DTF-05")
    technique_text = models.TextField(blank=True)
    sample_description = models.TextField(blank=True)
    measurement_conditions = models.TextField(blank=True)
    results_text = models.TextField(blank=True)
    conclusions = models.TextField(blank=True)

    def __str__(self):
        return f"SIMS Report #{self.access_proposal_id}"

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
