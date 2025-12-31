from django.db import models
from django.conf import settings

# ========= Modelo de Avances para Confocal =========
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


# ========= Modelo de Diario de Entrada para Confocal =========
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
    solicitud = models.ForeignKey("ConfocalSolicitud", on_delete=models.CASCADE, related_name="diario")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateField()
    etapa = models.CharField(max_length=20, choices=ETAPA)
    nota = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-creado_en"]

    def __str__(self):
        return f"Diario Confocal {self.solicitud_id} {self.fecha} {self.etapa}"


# ========= Modelo de Solicitud de Modificación para Confocal =========
class ConfocalSolicitudModificacion(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de revisión'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]
    
    TIPO_MODIFICACION_CHOICES = [
        ('numero_muestras', 'Cambiar número de muestras'),
        ('tipo_microscopia', 'Cambiar tipo de microscopía'),
        ('parametros_confocal', 'Modificar parámetros de confocal'),
        ('requisitos_finales', 'Modificar requisitos finales'),
        ('etapas_preparacion', 'Añadir/quitar etapas de preparación'),
        ('observaciones', 'Modificar observaciones'),
        ('otro_dato_importante', 'Modificar otros datos importantes'),
        ('manejo_especial', 'Modificar manejo especial'),
        ('tratamiento_previo', 'Modificar tratamiento previo'),
        ('procedencia', 'Modificar procedencia'),
        ('otro', 'Otra modificación'),
    ]
    
    # Relación con la solicitud original
    solicitud_original = models.ForeignKey(
        'ConfocalSolicitud', 
        on_delete=models.CASCADE, 
        related_name='modificaciones',
        help_text="Solicitud original que se quiere modificar"
    )
    
    # Información de la modificación
    tipo_modificacion = models.CharField(
        max_length=50, 
        choices=TIPO_MODIFICACION_CHOICES,
        help_text="Tipo de modificación solicitada"
    )
    descripcion_cambio = models.TextField(
        help_text="Descripción detallada del cambio solicitado"
    )
    justificacion = models.TextField(
        help_text="Justificación del cambio solicitado"
    )
    
    # Campos modificados (JSON para flexibilidad)
    cambios_solicitados = models.JSONField(
        default=dict,
        help_text="Campos específicos que se quieren modificar"
    )
    
    # Estado y fechas
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='pendiente'
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    
    # Usuarios involucrados
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='modificaciones_confocal_solicitadas'
    )
    tecnico_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='modificaciones_confocal_revisadas',
        null=True, 
        blank=True
    )
    
    # Comentarios del técnico
    comentarios_tecnico = models.TextField(
        blank=True,
        help_text="Comentarios del técnico sobre la modificación"
    )
    
    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = "Solicitud de Modificación Confocal"
        verbose_name_plural = "Solicitudes de Modificación Confocal"
    
    def __str__(self):
        return f"Modificación Confocal #{self.pk} - {self.solicitud_original} - {self.get_estado_display()}"


# ========= Modelo de Anulación de Solicitud Confocal =========
class ConfocalSolicitudAnulacion(models.Model):
    # Relación con la solicitud
    solicitud = models.ForeignKey(
        'ConfocalSolicitud', 
        on_delete=models.CASCADE, 
        related_name='anulaciones',
        help_text="Solicitud que se anula"
    )
    
    # Información de la anulación
    justificacion = models.TextField(
        help_text="Justificación de por qué se anula la solicitud"
    )
    
    # Fecha y usuario
    fecha_anulacion = models.DateTimeField(auto_now_add=True)
    usuario_anulacion = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='solicitudes_confocal_anuladas',
        help_text="Usuario que anula la solicitud"
    )
    
    # Tipo de anulación
    TIPO_ANULACION_CHOICES = [
        ('usuario_pendiente', 'Anulación por usuario (solicitud pendiente)'),
        ('usuario_aceptada', 'Anulación por usuario (solicitud aceptada)'),
        ('tecnico', 'Anulación por técnico'),
        ('sistema', 'Anulación automática del sistema'),
    ]
    
    tipo_anulacion = models.CharField(
        max_length=20,
        choices=TIPO_ANULACION_CHOICES,
        default='usuario_pendiente',
        help_text="Tipo de anulación"
    )
    
    class Meta:
        ordering = ['-fecha_anulacion']
        verbose_name = "Anulación de Solicitud Confocal"
        verbose_name_plural = "Anulaciones de Solicitudes Confocal"
    
    def __str__(self):
        return f"Anulación Confocal #{self.pk} - {self.solicitud} - {self.get_tipo_anulacion_display()}"

