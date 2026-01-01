from django.db import models


class DirectServiceRequest(models.Model):
    REQUESTED_SERVICE_CHOICES = [
        ("SEM", "SEM"),
        ("Confocal", "Confocal"),
        ("SIMS", "SIMS"),
        ("Profilometer", "Profilometer"),
        ("Dielectric", "Dielectric"),
        ("VDG", "VDG"),
        ("OLMAT", "OLMAT"),
        ("LML", "LML"),
        ("Otro", "Otro"),
    ]
    STATUS_CHOICES = [
        ("received", "received"),
        ("forwarded", "forwarded"),
        ("closed", "closed"),
    ]

    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    requested_service = models.CharField(
        max_length=50,
        choices=REQUESTED_SERVICE_CHOICES,
    )
    message = models.TextField(blank=True)
    form_pdf = models.FileField(
        upload_to="direct_requests/%Y/%m/",
        blank=True,
        null=True,
    )
    is_digitally_signed = models.BooleanField(default=False)
    consent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="received",
    )

    def __str__(self):
        return f"{self.full_name} - {self.requested_service}"
