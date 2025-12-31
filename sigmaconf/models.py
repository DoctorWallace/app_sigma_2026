from django.db import models, transaction
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from icts.models import AccessProposal

# ========= Modelo de Muestra Individual para Confocal =========
class ConfocalMuestraIndividual(models.Model):
    solicitud = models.ForeignKey('ConfocalSolicitud', on_delete=models.CASCADE, related_name='muestras')
    numero_secuencia = models.PositiveIntegerField(help_text="Número de secuencia (1, 2, 3, etc.)")
    identificacion = models.CharField(max_length=200, help_text="Identificación que le da el usuario")
    descripcion = models.TextField(blank=True, help_text="Descripción adicional de la muestra")
    
    class Meta:
        ordering = ['numero_secuencia']
        unique_together = ['solicitud', 'numero_secuencia']
        verbose_name = "Muestra Individual Confocal"
        verbose_name_plural = "Muestras Individuales Confocal"
    
    def __str__(self):
        return f"{self.solicitud.codigo_muestra}_{self.numero_secuencia} - {self.identificacion}"
    
    @property
    def codigo_completo(self):
        """Genera el código completo como 25_033_1, 25_033_2, etc."""
        if self.solicitud.codigo_muestra:
            return f"{self.solicitud.codigo_muestra}_{self.numero_secuencia}"
        return f"PENDIENTE_{self.numero_secuencia}"


# ========= Modelo de Solicitudes Confocal =========
class ConfocalSolicitud(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ACEPTADA = "aceptada", "Aceptada"
        RECHAZADA = "rechazada", "Rechazada"
        EN_CURSO = "en_curso", "En curso"
        FINALIZADA = "finalizada", "Finalizada"
        ANULADA = "anulada", "Anulada"

    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="solicitudes_confocal"
    )
    tecnico_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="solicitudes_confocal_asignadas",
    )
    
    # Becario asociado (opcional)
    becario_asociado = models.ForeignKey(
        'sigmalab.UsuarioAsociado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_confocal_realizadas",
        help_text="Becario que realizó la solicitud (si aplica)"
    )
    
    # Fecha de inicio de trabajo en laboratorio
    fecha_inicio_trabajo = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de inicio del trabajo en el laboratorio"
    )

    # Información básica de la solicitud
    material = models.CharField(max_length=200, blank=True)
    numero_muestras = models.PositiveIntegerField(default=1, help_text="Número de muestras a procesar")
    
    # Información específica de confocal
    tipo_microscopia = models.CharField(
        max_length=50,
        choices=[
            ('confocal_laser', 'Microscopía Confocal Láser'),
            ('confocal_spinning', 'Microscopía Confocal Spinning Disk'),
            ('super_resolucion', 'Microscopía de Super Resolución'),
            ('multifoton', 'Microscopía Multifotón'),
            ('otra', 'Otra'),
        ],
        default='confocal_laser',
        help_text="Tipo de microscopía confocal requerida"
    )
    
    # Parámetros específicos de confocal
    longitud_onda_excitacion = models.CharField(
        max_length=100,
        blank=True,
        help_text="Longitud de onda de excitación requerida (nm)"
    )
    longitud_onda_emision = models.CharField(
        max_length=100,
        blank=True,
        help_text="Longitud de onda de emisión esperada (nm)"
    )
    objetivo_requerido = models.CharField(
        max_length=100,
        blank=True,
        help_text="Objetivo requerido (ej: 40x, 63x, 100x)"
    )
    espesor_muestra = models.CharField(
        max_length=50,
        blank=True,
        help_text="Espesor de la muestra (μm)"
    )
    
    # Información de tinción y preparación
    tincion_utilizada = models.TextField(
        blank=True,
        help_text="Tinción o marcaje utilizado en la muestra"
    )
    preparacion_muestra = models.TextField(
        blank=True,
        help_text="Descripción de la preparación de la muestra"
    )
    
    # Información de seguridad y manejo
    material_radioactivo = models.BooleanField(default=False, help_text="¿Es material radiactivo o contaminado?")
    manejo_especial = models.TextField(blank=True, help_text="¿Requiere algún tipo de manejo o protección especial?")
    tratamiento_previo = models.TextField(blank=True, help_text="¿Se ha realizado algún tratamiento previo?")
    
    # Información de procedencia y descripción
    procedencia = models.CharField(max_length=200, blank=True)
    otro_dato_importante = models.TextField(blank=True, help_text="Otro dato importante de la muestra")
    
    # Requisitos y observaciones
    requisitos_finales = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    
    # Archivos adjuntos
    imagen_muestra = models.ImageField(upload_to="confocal/imagenes/", blank=True, null=True, help_text="Adjuntar imagen de la muestra")
    croquis = models.ImageField(upload_to="confocal/croquis/", blank=True, null=True, help_text="Adjuntar croquis")
    
    # Tiempo estimado de finalización
    tiempo_estimado_numero = models.PositiveIntegerField(
        null=True, blank=True, 
        help_text="Número de unidades de tiempo estimadas (1-30)"
    )
    tiempo_estimado_unidad = models.CharField(
        max_length=10, 
        choices=[
            ('dias', 'Días'),
            ('semanas', 'Semanas'),
            ('meses', 'Meses'),
        ],
        blank=True,
        help_text="Unidad de tiempo estimada"
    )
    tiempo_estimado_indeterminado = models.BooleanField(
        default=False,
        help_text="Marcar si el tiempo de finalización es indeterminado"
    )
    fecha_estimada_finalizacion = models.DateTimeField(
        null=True, blank=True,
        help_text="Fecha calculada de finalización basada en la estimación"
    )

    # Operaciones de preparación específicas para confocal
    montaje_fluorescente = models.BooleanField(default=False, help_text="Montaje en medio fluorescente")
    fijacion = models.BooleanField(default=False, help_text="Fijación de la muestra")
    deshidratacion = models.BooleanField(default=False, help_text="Deshidratación")
    inclusion = models.BooleanField(default=False, help_text="Inclusión en resina")
    corte_fino = models.BooleanField(default=False, help_text="Corte fino")
    tincion_histologica = models.BooleanField(default=False, help_text="Tinción histológica")
    inmunotincion = models.BooleanField(default=False, help_text="Inmunotinción")
    tincion_nuclear = models.BooleanField(default=False, help_text="Tinción nuclear (DAPI, Hoechst, etc.)")

    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    autonomo = models.BooleanField(
        default=False, help_text="Usuario validado como autónomo para esta solicitud"
    )
    codigo_muestra = models.CharField(
        max_length=20, blank=True, null=True, help_text="Se puede asignar al aceptar (p.ej. 25-001)"
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    aceptado_en = models.DateTimeField(null=True, blank=True)
    finalizado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Solicitud Confocal"
        verbose_name_plural = "Solicitudes Confocal"

    def __str__(self):
        return f"CONF#{self.pk or '-'} – {self.solicitante} – {self.estado}"


class ConfocalAvance(models.Model):
    TIPO = (("avance", "Avance"), ("nota", "Nota interna"))

    solicitud = models.ForeignKey("ConfocalSolicitud", on_delete=models.CASCADE, related_name="avances")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="avances_confocal_publicados"
    )
    tipo = models.CharField(max_length=10, choices=TIPO, default="avance")
    contenido = models.TextField()
    adjunto = models.FileField(upload_to="confocal/avances/", blank=True, null=True)
    visible_para_usuario = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado_en"]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.solicitud} - {self.creado_en:%Y-%m-%d %H:%M}"


class ConfocalDiarioEntrada(models.Model):
    ETAPA = (
        ("montaje_fluorescente", "Montaje Fluorescente"),
        ("fijacion", "Fijación"),
        ("deshidratacion", "Deshidratación"),
        ("inclusion", "Inclusión"),
        ("corte_fino", "Corte Fino"),
        ("tincion_histologica", "Tinción Histológica"),
        ("inmunotincion", "Inmunotinción"),
        ("tincion_nuclear", "Tinción Nuclear"),
        ("microscopia", "Microscopía"),
        ("procesamiento_imagen", "Procesamiento de Imagen"),
        ("otra", "Otra"),
    )
    solicitud = models.ForeignKey(ConfocalSolicitud, on_delete=models.CASCADE, related_name="diario")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateField()
    etapa = models.CharField(max_length=20, choices=ETAPA)
    nota = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-creado_en"]

    def __str__(self):
        return f"Diario Confocal {self.solicitud_id} {self.fecha} {self.etapa}"


class MCFYearCounter(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    counter = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["year"]
        verbose_name = "MCF year counter"
        verbose_name_plural = "MCF year counters"

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


class MCFSession(models.Model):
    STATUS_CHOICES = (
        ("in_progress", "In progress"),
        ("completed", "Completed"),
    )

    access_proposal = models.ForeignKey(
        AccessProposal, on_delete=models.CASCADE, related_name="mcf_sessions"
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="mcf_sessions"
    )
    lot_code = models.CharField(max_length=20, unique=True)
    report_code = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completion_date = models.DateField(null=True, blank=True)
    notice_pdf = models.FileField(upload_to="mcf/notices/", blank=True, null=True)
    final_report_pdf = models.FileField(upload_to="mcf/final_reports/", blank=True, null=True)
    final_report_uploaded_at = models.DateTimeField(null=True, blank=True)
    final_report_uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="mcf_final_reports",
        null=True,
        blank=True,
    )
    request_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "MCF session"
        verbose_name_plural = "MCF sessions"

    def __str__(self):
        return f"{self.lot_code} - {self.access_proposal.title}"

    def _assign_lot_code(self):
        year_full = timezone.now().year
        counter = MCFYearCounter.next_counter(year_full)
        year_short = year_full % 100
        return f"MCF-{year_short:02d}-{counter:03d}"

    def save(self, *args, **kwargs):
        if not self.request_snapshot and self.access_proposal_id:
            payload = self.access_proposal.facility_data or {}
            if isinstance(payload, dict):
                self.request_snapshot = payload.get("confocal", {}) or {}
        if not self.lot_code:
            with transaction.atomic():
                self.lot_code = self._assign_lot_code()
                if not self.report_code:
                    self.report_code = f"IN-DTF-{self.lot_code}"
        elif not self.report_code:
            self.report_code = f"IN-DTF-{self.lot_code}"
        super().save(*args, **kwargs)


class MCFSampleRecord(models.Model):
    SOURCE_CHOICES = (
        ("proposal", "Proposal"),
        ("session", "Session"),
    )

    session = models.ForeignKey(
        MCFSession, on_delete=models.CASCADE, related_name="samples"
    )
    sequence = models.PositiveIntegerField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="proposal")
    identification = models.CharField(max_length=200)
    name = models.CharField(max_length=200, blank=True)
    details = models.TextField(blank=True)
    received_date = models.DateField(null=True, blank=True)
    analysis_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    report_delivery_date = models.DateField(null=True, blank=True)
    operator_name = models.CharField(max_length=200, blank=True)
    roughness = models.BooleanField(default=False)
    image_2d = models.BooleanField(default=False)
    image_3d = models.BooleanField(default=False)
    thickness = models.BooleanField(default=False)
    report_code = models.CharField(max_length=40, blank=True)
    observations = models.TextField(blank=True)
    indicator_i1 = models.PositiveSmallIntegerField(default=0)
    indicator_i2 = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sequence"]
        unique_together = [("session", "sequence")]
        verbose_name = "MCF sample record"
        verbose_name_plural = "MCF sample records"

    def __str__(self):
        return f"{self.session.lot_code} #{self.sequence} - {self.identification}"

    def save(self, *args, **kwargs):
        if not self.operator_name and self.session_id:
            tech = self.session.technician
            if tech:
                self.operator_name = tech.get_full_name() or tech.get_username()
        if not self.report_code and self.session_id:
            self.report_code = self.session.report_code
        super().save(*args, **kwargs)


class LO3Conversation(models.Model):
    access_proposal = models.OneToOneField(
        AccessProposal, on_delete=models.CASCADE, related_name="lo3_conversation"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "LO3 conversation"
        verbose_name_plural = "LO3 conversations"

    def __str__(self):
        code = self.access_proposal.access_code or f"#{self.access_proposal_id}"
        return f"LO3 convo {code}"


class LO3Message(models.Model):
    conversation = models.ForeignKey(
        LO3Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lo3_messages",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at_applicant = models.DateTimeField(null=True, blank=True)
    read_at_technician = models.DateTimeField(null=True, blank=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "LO3 message"
        verbose_name_plural = "LO3 messages"

    def __str__(self):
        preview = (self.body or "")[:40]
        return f"LO3 message {self.id}: {preview}"


class LO3MessageAttachment(models.Model):
    message = models.ForeignKey(
        LO3Message, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="lo3/communications/")
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lo3_message_attachments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "LO3 message attachment"
        verbose_name_plural = "LO3 message attachments"

    def __str__(self):
        return self.filename or f"Attachment {self.id}"


class LO3Equipment(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("maintenance", "Maintenance"),
        ("inactive", "Inactive"),
    )

    name = models.CharField(max_length=200)
    manufacturer = models.CharField(max_length=200, blank=True)
    model = models.CharField(max_length=200, blank=True)
    serial_number = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "LO3 equipment"
        verbose_name_plural = "LO3 equipment"

    def __str__(self):
        return self.name


class LO3EquipmentDocument(models.Model):
    DOC_TYPE_CHOICES = (
        ("manual", "Manual"),
        ("sop", "SOP"),
        ("procedure", "Procedure"),
        ("other", "Other"),
    )

    equipment = models.ForeignKey(
        LO3Equipment, on_delete=models.CASCADE, related_name="documents"
    )
    file = models.FileField(upload_to="lo3/equipment/")
    title = models.CharField(max_length=200)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, default="other")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lo3_equipment_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "LO3 equipment document"
        verbose_name_plural = "LO3 equipment documents"

    def __str__(self):
        return self.title or f"Document {self.id}"


class LO3Attachment(models.Model):
    ATTACHMENT_TYPE_CHOICES = (
        ("photo", "Foto"),
        ("rawdata", "Raw data"),
        ("report", "Informe"),
        ("other", "Otro"),
    )

    session = models.ForeignKey(
        MCFSession,
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,
        blank=True,
    )
    sample = models.ForeignKey(
        MCFSampleRecord,
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,
        blank=True,
    )
    file = models.FileField(upload_to="lo3/attachments/")
    attachment_type = models.CharField(
        max_length=20, choices=ATTACHMENT_TYPE_CHOICES, default="other"
    )
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lo3_attachments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(session__isnull=False) | Q(sample__isnull=False),
                name="lo3_attachment_has_owner",
            )
        ]
        verbose_name = "LO3 attachment"
        verbose_name_plural = "LO3 attachments"

    def __str__(self):
        return f"Attachment {self.id}"


class LO3Calibration(models.Model):
    CALIBRATION_TYPE_CHOICES = (
        ("internal", "Internal"),
        ("external", "External"),
    )

    equipment = models.ForeignKey(
        LO3Equipment, on_delete=models.CASCADE, related_name="calibrations"
    )
    calibration_type = models.CharField(
        max_length=20, choices=CALIBRATION_TYPE_CHOICES, default="internal"
    )
    performed_at = models.DateField()
    due_at = models.DateField(null=True, blank=True)
    performed_by = models.CharField(max_length=200, blank=True)
    provider = models.CharField(max_length=200, blank=True)
    certificate_file = models.FileField(
        upload_to="lo3/calibrations/", null=True, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-performed_at"]
        verbose_name = "LO3 calibration"
        verbose_name_plural = "LO3 calibrations"

    def __str__(self):
        return f"{self.get_calibration_type_display()} {self.equipment.name}"


class LO3ReferenceMaterial(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("retired", "Retired"),
    )

    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255)
    catalog_reference = models.CharField(max_length=200, blank=True)
    responsible = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    reception_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    observations = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "LO3 reference material"
        verbose_name_plural = "LO3 reference materials"

    def __str__(self):
        return self.code


class LO3ReferenceMaterialDocument(models.Model):
    material = models.ForeignKey(
        LO3ReferenceMaterial, on_delete=models.CASCADE, related_name="documents"
    )
    file = models.FileField(upload_to="lo3/reference_materials/")
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "LO3 reference material document"
        verbose_name_plural = "LO3 reference material documents"

    def __str__(self):
        return self.title or f"Document {self.id}"


class LO3Incident(models.Model):
    INCIDENT_TYPE_CHOICES = (
        ("control_intermedio", "Control intermedio"),
        ("incidencia", "Incidencia"),
    )
    SEVERITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    )
    STATUS_CHOICES = (
        ("open", "Open"),
        ("in_progress", "In progress"),
        ("closed", "Closed"),
    )

    incident_type = models.CharField(
        max_length=30, choices=INCIDENT_TYPE_CHOICES, default="incidencia"
    )
    equipment = models.ForeignKey(
        LO3Equipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidents",
    )
    session = models.ForeignKey(
        MCFSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incidents",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="low")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    corrective_actions = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lo3_incidents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "LO3 incident"
        verbose_name_plural = "LO3 incidents"

    def __str__(self):
        return self.title


class LO3IncidentAttachment(models.Model):
    incident = models.ForeignKey(
        LO3Incident, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="lo3/incidents/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lo3_incident_attachments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "LO3 incident attachment"
        verbose_name_plural = "LO3 incident attachments"

    def __str__(self):
        return f"Attachment {self.id}"


class LO3Habilitation(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("revoked", "Revoked"),
    )

    investigator_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lo3_habilitations",
    )
    investigator_full_name = models.CharField(max_length=200, blank=True)
    ciemat_id = models.CharField(max_length=100, blank=True)
    department_division = models.CharField(max_length=200, blank=True)
    center_university = models.CharField(max_length=200, blank=True)
    equipment = models.ForeignKey(
        LO3Equipment, on_delete=models.PROTECT, related_name="habilitations"
    )
    issued_at = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.TextField(blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lo3_habilitations_issued",
    )
    certificate_pdf = models.FileField(upload_to="lo3/habilitations/", blank=True)
    linked_technician_account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lo3_habilitations_linked",
    )

    class Meta:
        ordering = ["-issued_at"]
        verbose_name = "LO3 habilitation"
        verbose_name_plural = "LO3 habilitations"

    def __str__(self):
        name = self.investigator_full_name
        if not name and self.investigator_user:
            name = self.investigator_user.get_full_name() or self.investigator_user.username
        return f"Habilitacion {name or ''}".strip()
