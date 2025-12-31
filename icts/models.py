# icts/models.py
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

# --- Modelos principales ICTS ---

class Facility(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class AccessProposal(models.Model):
    ICTS_TECH_FIELDS = (
        "facility_sem",
        "facility_sem_fib",
        "facility_imp",
        "facility_sims",
        "facility_confocal",
        "facility_vdg",
        "facility_profilometer",
    )
    PROJECT_TYPE_CHOICES = [
        ("international", "International"),
        ("european", "European"),
        ("national", "National"),
        ("regional", "Regional"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("changes_requested", "Changes requested"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]
    
    # Información básica
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="icts_proposals",
    )
    title = models.CharField(max_length=200)
    scope = models.TextField(blank=True)
    facilities = models.ManyToManyField(Facility, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    responsable_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    # Campos adicionales del template de prueba
    is_new_request = models.BooleanField(default=True, help_text="Is this a new request?")
    previous_access = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Previous approved request to copy data from"
    )
    access_code = models.CharField(max_length=80, blank=True, help_text="Auto-generated access code")
    user_sequence_number = models.PositiveIntegerField(null=True, blank=True)
    
    # Información del solicitante (cuando es diferente del usuario registrado)
    applicant_is_different = models.BooleanField(default=False)
    organization = models.CharField(max_length=200, blank=True, help_text="Center/Institution")
    contact_person = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    
    # Información del proyecto de financiación
    project_name = models.CharField(max_length=200, blank=True)
    project_type = models.CharField(
        max_length=100,
        blank=True,
        choices=PROJECT_TYPE_CHOICES,
        help_text="International, European, National, Regional",
    )
    funding_source = models.CharField(max_length=200, blank=True)
    start_year = models.IntegerField(null=True, blank=True)
    end_year = models.IntegerField(null=True, blank=True)
    
    # Experimentos previos y referencias
    previous_experiments = models.TextField(blank=True)
    references = models.TextField(blank=True)
    
    # Facilidades específicas (checkboxes individuales)
    facility_sem = models.BooleanField(default=False)
    facility_sem_fib = models.BooleanField(default=False)
    facility_imp = models.BooleanField(default=False)
    facility_sims = models.BooleanField(default=False)
    facility_confocal = models.BooleanField(default=False)
    facility_vdg = models.BooleanField(default=False)
    facility_profilometer = models.BooleanField(default=False)
    facility_olmat = models.BooleanField(default=False)

    # Datos específicos por técnica (estructura libre, por ejemplo capturado desde subformularios dinámicos)
    facility_data = models.JSONField(null=True, blank=True, default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["applicant", "user_sequence_number"],
                condition=models.Q(user_sequence_number__isnull=False),
                name="unique_accessproposal_user_sequence",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def has_icts_techniques(self) -> bool:
        """True when any ICTS technique (excluding OLMAT) is selected."""
        return any(getattr(self, field, False) for field in self.ICTS_TECH_FIELDS)

    @property
    def is_olmat_only(self) -> bool:
        """True when OLMAT is selected without any other ICTS techniques."""
        return bool(self.facility_olmat) and not self.has_icts_techniques


class Participant(models.Model):
    proposal = models.ForeignKey(
        AccessProposal, on_delete=models.CASCADE, related_name="participants"
    )
    name = models.CharField(max_length=120, help_text="Full name of participant")
    center = models.CharField(max_length=200, blank=True, help_text="Center/Institution")
    address = models.TextField(blank=True, help_text="Address")

    def __str__(self):
        return f"{self.name} — {self.proposal.title}"


class ProposalReview(models.Model):
    DECISION = [
        ("pending", "Pending"),
        ("approve", "Approve"),
        ("request_changes", "Request changes"),
        ("reject", "Reject"),
    ]
    proposal = models.ForeignKey(
        AccessProposal, on_delete=models.CASCADE, related_name="reviews"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="icts_reviews"
    )
    decision = models.CharField(max_length=16, choices=DECISION, default="pending")
    comments = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Campos adicionales del template de revisión
    feasibility_ok = models.BooleanField(null=True, blank=True, help_text="Is this proposal technically feasible?")
    score_scientific_quality = models.IntegerField(
        null=True, blank=True, 
        choices=[(i, i) for i in range(1, 6)],
        help_text="Scientific quality score (1-5)"
    )
    score_need_infrastructure = models.IntegerField(
        null=True, blank=True,
        choices=[(i, i) for i in range(1, 6)],
        help_text="Need for advanced infrastructure score (1-5)"
    )
    score_industrial_potential = models.IntegerField(
        null=True, blank=True,
        choices=[(i, i) for i in range(1, 6)],
        help_text="Industrial potential score (1-5)"
    )

    class Meta:
        unique_together = ("proposal", "reviewer")

    def __str__(self):
        return f"Review {self.proposal_id} by {self.reviewer} -> {self.decision}"


class ProposalAttachment(models.Model):
    """Archivos adjuntos a las propuestas"""
    proposal = models.ForeignKey(
        AccessProposal, on_delete=models.CASCADE, related_name="attachments"
    )
    name = models.CharField(max_length=200, help_text="Document name")
    file = models.FileField(upload_to="proposal_attachments/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.proposal.title}"


# --- Perfil de usuario ICTS (datos adicionales del registro) ---

User = get_user_model()

class ICTSUserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="icts_profile"
    )
    center = models.CharField("Centro / Institución", max_length=150, blank=True)
    phone = models.CharField("Teléfono", max_length=30, blank=True)
    address = models.TextField("Dirección", blank=True)
    user_siglas = models.CharField("Siglas usuario", max_length=10, blank=True, null=True, unique=True)
    proposal_counter = models.PositiveIntegerField(default=0)
    validated = models.BooleanField("Validado por responsable", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Campos CIEMAT
    matricula = models.CharField("Matrícula CIEMAT", max_length=50, blank=True)

    def __str__(self):
        return f"Perfil ICTS de {self.user.get_username()}"


# --- Modelo específico para solicitudes OLMAT ---

class OLMATRequest(models.Model):
    ENTITY_TYPE_CHOICES = [
        ("public", "Entidad pública"),
        ("private", "Entidad privada"),
        ("mixed", "Entidad mixta / otra"),
    ]
    SERVICE_TYPE_CHOICES = [
        ("technical", "Servicio técnico (5.000 €)"),
        ("research", "Servicio de investigación (10.305 €)"),
    ]
    
    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("under_review", "En revisión"),
        ("approved", "Aprobado"),
        ("rejected", "Rechazado"),
        ("completed", "Completado"),
    ]
    
    # Información básica
    proposal = models.OneToOneField(
        AccessProposal, 
        on_delete=models.CASCADE, 
        related_name="olmat_request"
    )
    proponent_name = models.CharField(
        max_length=200,
        help_text="Nombre del proponente o investigador principal",
        blank=True,
    )
    proponent_affiliation = models.CharField(
        max_length=200,
        help_text="Afiliación del proponente",
        blank=True,
    )
    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPE_CHOICES,
        blank=True,
        default="",
        help_text="Naturaleza de la entidad (pública/privada/mixta)",
    )
    activity_description = models.TextField(
        blank=True,
        help_text="Descripción breve (1-2 páginas) con motivación, objetivos y alcance",
    )
    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES,
        help_text="Tipo de servicio solicitado"
    )
    access_code = models.CharField(
        max_length=120,
        blank=True,
        help_text="Código específico de la solicitud OLMAT"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="pending"
    )
    
    # Campos específicos de OLMAT
    irradiation_requirements = models.TextField(
        blank=True, 
        help_text="Requisitos de irradiación de la carga de calor"
    )
    diagnostics_needed = models.JSONField(
        default=list, 
        help_text="Diagnósticos necesarios (termopares, pirometría, etc.)"
    )
    sample_preparation = models.JSONField(
        default=list, 
        help_text="Preparación de muestras requerida"
    )
    beam_usage = models.JSONField(
        default=list, 
        help_text="Uso de haz (NBI, láser, ambos)"
    )
    preferred_dates = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="Fechas preferidas para el experimento"
    )
    flexibility = models.CharField(
        max_length=20, 
        choices=[
            ("high", "Alta flexibilidad"),
            ("medium", "Flexibilidad media"),
            ("low", "Baja flexibilidad"),
        ],
        default="medium"
    )
    additional_requirements = models.TextField(
        blank=True, 
        help_text="Requisitos adicionales específicos"
    )
    
    # Información de evaluación
    evaluation_notes = models.TextField(
        blank=True, 
        help_text="Notas de evaluación del equipo OLMAT"
    )
    estimated_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Coste estimado del servicio"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Solicitud OLMAT - {self.proposal.title} ({self.get_service_type_display()})"
    
    @property
    def base_cost(self):
        """Retorna el coste base según el tipo de servicio"""
        if self.service_type == "technical":
            return 5000.00
        elif self.service_type == "research":
            return 10305.00
        return 0.00
