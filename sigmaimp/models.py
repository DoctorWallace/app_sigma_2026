from django.conf import settings
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from icts.models import AccessProposal


class IMPYearCounter(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    counter = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["year"]
        verbose_name = "IMP year counter"
        verbose_name_plural = "IMP year counters"

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


class IMPSession(models.Model):
    STATUS_CHOICES = (
        ("in_progress", "In progress"),
        ("completed", "Completed"),
    )

    access_proposal = models.ForeignKey(
        AccessProposal, on_delete=models.CASCADE, related_name="imp_sessions"
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="imp_sessions"
    )
    session_code = models.CharField(max_length=30, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notice_pdf = models.FileField(upload_to="imp/notices/", null=True, blank=True)
    final_report_pdf = models.FileField(upload_to="imp/final_reports/", null=True, blank=True)
    final_report_uploaded_at = models.DateTimeField(null=True, blank=True)
    final_report_uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="imp_final_reports",
        null=True,
        blank=True,
    )
    request_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "IMP session"
        verbose_name_plural = "IMP sessions"

    def __str__(self):
        return f"{self.session_code} - {self.access_proposal.title}"

    def _build_session_code(self):
        year_full = timezone.now().year
        counter = IMPYearCounter.next_counter(year_full)
        prefix = getattr(settings, "IMP_SESSION_CODE_PREFIX", "IMP")
        fmt = getattr(
            settings,
            "IMP_SESSION_CODE_FORMAT",
            "{prefix}-{year_short:02d}-{counter:03d}",
        )
        return fmt.format(
            prefix=prefix,
            year_full=year_full,
            year_short=year_full % 100,
            counter=counter,
        )

    def save(self, *args, **kwargs):
        if not self.request_snapshot and self.access_proposal_id:
            payload = self.access_proposal.facility_data or {}
            if isinstance(payload, dict):
                self.request_snapshot = payload.get("imp", {}) or {}
        if not self.session_code:
            with transaction.atomic():
                self.session_code = self._build_session_code()
        super().save(*args, **kwargs)


class IMPSampleRecord(models.Model):
    SOURCE_CHOICES = (
        ("proposal", "Proposal"),
        ("session", "Session"),
    )

    session = models.ForeignKey(
        IMPSession, on_delete=models.CASCADE, related_name="samples"
    )
    sequence = models.PositiveIntegerField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="proposal")
    identification = models.CharField(max_length=200)
    name = models.CharField(max_length=200, blank=True)
    details = models.TextField(blank=True)
    received_date = models.DateField(null=True, blank=True)
    implant_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    destroyed = models.BooleanField(default=False)
    destroyed_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["sequence"]
        unique_together = [("session", "sequence")]
        verbose_name = "IMP sample record"
        verbose_name_plural = "IMP sample records"

    def __str__(self):
        return f"{self.session.session_code} #{self.sequence} - {self.identification}"


class IMPAttachment(models.Model):
    ATTACHMENT_TYPE_CHOICES = (
        ("photo", "Photo"),
        ("rawdata", "Raw data"),
        ("report", "Report"),
        ("other", "Other"),
    )

    session = models.ForeignKey(
        IMPSession,
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,
        blank=True,
    )
    sample = models.ForeignKey(
        IMPSampleRecord,
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,
        blank=True,
    )
    file = models.FileField(upload_to="imp/attachments/")
    attachment_type = models.CharField(
        max_length=20, choices=ATTACHMENT_TYPE_CHOICES, default="other"
    )
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="imp_attachments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(session__isnull=False) | Q(sample__isnull=False),
                name="imp_attachment_has_owner",
            )
        ]
        verbose_name = "IMP attachment"
        verbose_name_plural = "IMP attachments"

    def __str__(self):
        return f"Attachment {self.id}"


class IMPConversation(models.Model):
    access_proposal = models.OneToOneField(
        AccessProposal, on_delete=models.CASCADE, related_name="imp_conversation"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "IMP conversation"
        verbose_name_plural = "IMP conversations"

    def __str__(self):
        code = self.access_proposal.access_code or f"#{self.access_proposal_id}"
        return f"IMP convo {code}"


class IMPMessage(models.Model):
    conversation = models.ForeignKey(
        IMPConversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="imp_messages",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at_applicant = models.DateTimeField(null=True, blank=True)
    read_at_technician = models.DateTimeField(null=True, blank=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "IMP message"
        verbose_name_plural = "IMP messages"

    def __str__(self):
        preview = (self.body or "")[:40]
        return f"IMP message {self.id}: {preview}"


class IMPMessageAttachment(models.Model):
    message = models.ForeignKey(
        IMPMessage, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="imp/communications/")
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="imp_message_attachments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "IMP message attachment"
        verbose_name_plural = "IMP message attachments"

    def __str__(self):
        return self.filename or f"Attachment {self.id}"
