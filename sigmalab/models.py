from django.db import connection, models
from django.conf import settings
from django.utils import timezone


class SampleCodeSequence(models.Model):
    """Secuencia anual para códigos de muestra (garantiza atomicidad)."""

    year = models.PositiveIntegerField(unique=True)
    counter = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Secuencia códigos S-LAB"
        verbose_name_plural = "Secuencias códigos S-LAB"

    def __str__(self):
        return f"{self.year}: {self.counter}"

    @classmethod
    def next_counter(cls, year: int) -> int:
        """Incrementa y devuelve el contador para un año determinado."""
        manager = cls.objects
        lookup_kwargs = {"year": year}
        if connection.features.has_select_for_update:
            manager = manager.select_for_update()
        sequence, _ = manager.get_or_create(**lookup_kwargs)
        sequence.counter += 1
        sequence.save(update_fields=["counter", "updated_at"])
        return sequence.counter

    @classmethod
    def peek_next(cls, year: int) -> int:
        """Devuelve el siguiente contador sin modificar el estado."""
        current = cls.objects.filter(year=year).values_list("counter", flat=True).first() or 0
        return current + 1


# ========= Modelo de Muestra Individual =========
class MuestraIndividual(models.Model):
    solicitud = models.ForeignKey('Solicitud', on_delete=models.CASCADE, related_name='muestras')
    numero_secuencia = models.PositiveIntegerField(help_text="Número de secuencia (1, 2, 3, etc.)")
    identificacion = models.CharField(max_length=200, help_text="Identificación que le da el usuario")
    descripcion = models.TextField(blank=True, help_text="Descripción adicional de la muestra")
    
    class Meta:
        ordering = ['numero_secuencia']
        unique_together = ['solicitud', 'numero_secuencia']
        verbose_name = "Muestra Individual"
        verbose_name_plural = "Muestras Individuales"
    
    def __str__(self):
        return f"{self.solicitud.codigo_muestra}_{self.numero_secuencia} - {self.identificacion}"
    
    @property
    def codigo_completo(self):
        """Genera el código completo como 25_033_1, 25_033_2, etc."""
        if self.solicitud.codigo_muestra:
            return f"{self.solicitud.codigo_muestra}_{self.numero_secuencia}"
        return f"PENDIENTE_{self.numero_secuencia}"


# ========= Modelo mínimo de Muestra (legacy) =========
class Sample(models.Model):
    code = models.CharField("Código", max_length=20, unique=True)
    title = models.CharField("Título", max_length=200)
    notes = models.TextField("Notas", blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Propietario", on_delete=models.PROTECT
    )
    created_at = models.DateTimeField("Creado", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Muestra"
        verbose_name_plural = "Muestras"

    def __str__(self):
        return f"{self.code} – {self.title}"


# ========= Solicitudes (port de labrequest) =========
class Solicitud(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ACEPTADA = "aceptada", "Aceptada"
        RECHAZADA = "rechazada", "Rechazada"
        EN_CURSO = "en_curso", "En curso"
        FINALIZADA = "finalizada", "Finalizada"
        ANULADA = "anulada", "Anulada"

    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="solicitudes"
    )
    tecnico_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="solicitudes_asignadas",
    )
    
    # Becario asociado (opcional)
    becario_asociado = models.ForeignKey(
        'UsuarioAsociado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_realizadas",
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
    imagen_muestra = models.ImageField(upload_to="solicitudes/imagenes/", blank=True, null=True, help_text="Adjuntar imagen de la muestra")
    croquis = models.ImageField(upload_to="solicitudes/croquis/", blank=True, null=True, help_text="Adjuntar croquis")
    
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

    # Operaciones de preparación
    corte = models.BooleanField(default=False)
    empastillado = models.BooleanField(default=False)
    lijado = models.BooleanField(default=False)
    pulido = models.BooleanField(default=False)
    electropulido = models.BooleanField(default=False)
    trat_quimico = models.BooleanField(default=False)
    trat_termico = models.BooleanField(default=False)

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
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"

    def __str__(self):
        return f"SOL#{self.pk or '-'} – {self.solicitante} – {self.estado}"
    
    def calcular_fecha_estimada_finalizacion(self):
        """Calcula la fecha estimada de finalización basada en el tiempo estimado"""
        if self.tiempo_estimado_indeterminado or not self.tiempo_estimado_numero or not self.tiempo_estimado_unidad:
            return None
        
        from datetime import timedelta
        
        fecha_aceptacion = self.aceptado_en or timezone.now()
        
        if self.tiempo_estimado_unidad == 'dias':
            return fecha_aceptacion + timedelta(days=self.tiempo_estimado_numero)
        elif self.tiempo_estimado_unidad == 'semanas':
            return fecha_aceptacion + timedelta(weeks=self.tiempo_estimado_numero)
        elif self.tiempo_estimado_unidad == 'meses':
            # Aproximación: 1 mes = 30 días
            return fecha_aceptacion + timedelta(days=self.tiempo_estimado_numero * 30)
        
        return None
    
    def get_tiempo_estimado_display(self):
        """Retorna el tiempo estimado en formato legible"""
        if self.tiempo_estimado_indeterminado:
            return "Indeterminado"
        
        if not self.tiempo_estimado_numero or not self.tiempo_estimado_unidad:
            return "No especificado"
        
        unidad_display = dict(self._meta.get_field('tiempo_estimado_unidad').choices).get(
            self.tiempo_estimado_unidad, self.tiempo_estimado_unidad
        )
        
        return f"{self.tiempo_estimado_numero} {unidad_display}"
    
    def get_eficiencia_tiempo(self):
        """Calcula la eficiencia comparando tiempo estimado vs real"""
        if not self.finalizado_en or not self.aceptado_en:
            return None

        tiempo_real_segundos = (self.finalizado_en - self.aceptado_en).total_seconds()
        if tiempo_real_segundos <= 0:
            return None

        tiempo_real_dias = tiempo_real_segundos / 86400  # 60 * 60 * 24

        if self.tiempo_estimado_indeterminado:
            return None

        if not self.tiempo_estimado_numero or not self.tiempo_estimado_unidad:
            return None

        # Convertir tiempo estimado a días
        if self.tiempo_estimado_unidad == 'dias':
            tiempo_estimado_dias = self.tiempo_estimado_numero
        elif self.tiempo_estimado_unidad == 'semanas':
            tiempo_estimado_dias = self.tiempo_estimado_numero * 7
        elif self.tiempo_estimado_unidad == 'meses':
            tiempo_estimado_dias = self.tiempo_estimado_numero * 30
        else:
            return None

        if tiempo_estimado_dias <= 0:
            return None

        eficiencia = (tiempo_estimado_dias / tiempo_real_dias) * 100
        return round(eficiencia, 1)


class Avance(models.Model):
    TIPO = (("avance", "Avance"), ("nota", "Nota interna"))

    # Importante: referencia en cadena para evitar NameError por orden de clases
    solicitud = models.ForeignKey("sigmalab.Solicitud", on_delete=models.CASCADE, related_name="avances")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="avances_publicados"
    )
    tipo = models.CharField(max_length=10, choices=TIPO, default="avance")
    contenido = models.TextField()
    adjunto = models.FileField(upload_to="avances/", blank=True, null=True)
    visible_para_usuario = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado_en"]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.solicitud} - {self.creado_en:%Y-%m-%d %H:%M}"


class DiarioEntrada(models.Model):
    ETAPA = (
        ("corte", "Corte"),
        ("empastillado", "Empastillado"),
        ("lijado", "Lijado"),
        ("pulido", "Pulido"),
        ("electropulido", "Electropulido"),
        ("trat_quimico", "Tratamiento químico"),
        ("trat_termico", "Tratamiento térmico"),
        ("ensayo", "Ensayo máquina"),
        ("otra", "Otra"),
    )
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name="diario")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateField()
    etapa = models.CharField(max_length=20, choices=ETAPA)
    nota = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-creado_en"]

    def __str__(self):
        return f"Diario {self.solicitud_id} {self.fecha} {self.etapa}"


# ========= Modelo de Solicitud de Modificación =========
class SolicitudModificacion(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de revisión'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]
    
    TIPO_MODIFICACION_CHOICES = [
        ('numero_muestras', 'Cambiar número de muestras'),
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
        'Solicitud', 
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
        related_name='modificaciones_solicitadas'
    )
    tecnico_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='modificaciones_revisadas',
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
        verbose_name = "Solicitud de Modificación"
        verbose_name_plural = "Solicitudes de Modificación"
    
    def __str__(self):
        return f"Modificación #{self.pk} - {self.solicitud_original} - {self.get_estado_display()}"
    
    def puede_ser_modificada(self):
        """Verifica si la solicitud original puede ser modificada"""
        return self.solicitud_original.estado in ['aceptada', 'en_curso']
    
    def aplicar_cambios(self):
        """Aplica los cambios a la solicitud original si están aprobados"""
        if self.estado != 'aprobada':
            return False
        
        solicitud = self.solicitud_original
        
        # Aplicar cambios según el tipo
        if self.tipo_modificacion == 'numero_muestras':
            solicitud.numero_muestras = self.cambios_solicitados.get('numero_muestras', solicitud.numero_muestras)
        
        elif self.tipo_modificacion == 'requisitos_finales':
            solicitud.requisitos_finales = self.cambios_solicitados.get('requisitos_finales', solicitud.requisitos_finales)
        
        elif self.tipo_modificacion == 'etapas_preparacion':
            for etapa in ['corte', 'empastillado', 'lijado', 'pulido', 'electropulido', 'trat_quimico', 'trat_termico']:
                if etapa in self.cambios_solicitados:
                    setattr(solicitud, etapa, self.cambios_solicitados[etapa])
        
        elif self.tipo_modificacion == 'observaciones':
            solicitud.observaciones = self.cambios_solicitados.get('observaciones', solicitud.observaciones)
        
        elif self.tipo_modificacion == 'otro_dato_importante':
            solicitud.otro_dato_importante = self.cambios_solicitados.get('otro_dato_importante', solicitud.otro_dato_importante)
        
        elif self.tipo_modificacion == 'manejo_especial':
            solicitud.manejo_especial = self.cambios_solicitados.get('manejo_especial', solicitud.manejo_especial)
        
        elif self.tipo_modificacion == 'tratamiento_previo':
            solicitud.tratamiento_previo = self.cambios_solicitados.get('tratamiento_previo', solicitud.tratamiento_previo)
        
        elif self.tipo_modificacion == 'procedencia':
            solicitud.procedencia = self.cambios_solicitados.get('procedencia', solicitud.procedencia)
        
        solicitud.save()
        return True


# ========= Modelo de Anulación de Solicitud =========
class SolicitudAnulacion(models.Model):
    # Relación con la solicitud
    solicitud = models.ForeignKey(
        'Solicitud', 
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
        related_name='solicitudes_anuladas',
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
        verbose_name = "Anulación de Solicitud"
        verbose_name_plural = "Anulaciones de Solicitudes"
    
    def __str__(self):
        return f"Anulación #{self.pk} - {self.solicitud} - {self.get_tipo_anulacion_display()}"


# ========= Modelo de Incidencias del Laboratorio =========
class IncidenciaLaboratorio(models.Model):
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]
    
    CATEGORIA_CHOICES = [
        ('equipos', 'Equipos'),
        ('infraestructura', 'Infraestructura'),
        ('seguridad', 'Seguridad'),
        ('suministros', 'Suministros'),
        ('comunicaciones', 'Comunicaciones'),
        ('otros', 'Otros'),
    ]
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_revision', 'En revisión'),
        ('en_proceso', 'En proceso'),
        ('resuelta', 'Resuelta'),
        ('cerrada', 'Cerrada'),
    ]
    
    # Información básica de la incidencia
    titulo = models.CharField(
        max_length=200,
        help_text="Título descriptivo de la incidencia"
    )
    descripcion = models.TextField(
        help_text="Descripción detallada de la incidencia"
    )
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        help_text="Categoría de la incidencia"
    )
    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        default='media',
        help_text="Prioridad de la incidencia"
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='pendiente',
        help_text="Estado actual de la incidencia"
    )
    
    # Ubicación y contexto
    ubicacion = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ubicación específica donde ocurrió la incidencia"
    )
    equipos_afectados = models.CharField(
        max_length=200,
        blank=True,
        help_text="Equipos o sistemas afectados"
    )
    
    # Información de contacto y seguimiento
    reportado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='incidencias_reportadas',
        help_text="Usuario que reportó la incidencia"
    )
    asignado_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidencias_asignadas',
        help_text="Técnico asignado para resolver la incidencia"
    )
    
    # Fechas y seguimiento
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    fecha_asignacion = models.DateTimeField(null=True, blank=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    
    # Archivos adjuntos
    archivo_adjunto = models.FileField(
        upload_to='incidencias/archivos/',
        blank=True,
        null=True,
        help_text="Archivo adjunto (imagen, documento, etc.)"
    )
    
    # Información adicional
    impacto_operaciones = models.TextField(
        blank=True,
        help_text="Descripción del impacto en las operaciones del laboratorio"
    )
    acciones_inmediatas = models.TextField(
        blank=True,
        help_text="Acciones inmediatas tomadas o recomendadas"
    )
    
    class Meta:
        ordering = ['-fecha_reporte']
        verbose_name = "Incidencia del Laboratorio"
        verbose_name_plural = "Incidencias del Laboratorio"
    
    def __str__(self):
        return f"INC#{self.pk} - {self.titulo} - {self.get_estado_display()}"
    
    def get_prioridad_color(self):
        """Retorna el color CSS para la prioridad"""
        colors = {
            'baja': '#28a745',
            'media': '#ffc107',
            'alta': '#fd7e14',
            'critica': '#dc3545'
        }
        return colors.get(self.prioridad, '#6c757d')
    
    def get_estado_color(self):
        """Retorna el color CSS para el estado"""
        colors = {
            'pendiente': '#ffc107',
            'en_revision': '#17a2b8',
            'en_proceso': '#007bff',
            'resuelta': '#28a745',
            'cerrada': '#6c757d'
        }
        return colors.get(self.estado, '#6c757d')
    
    def tiempo_resolucion(self):
        """Calcula el tiempo transcurrido desde el reporte hasta la resolución"""
        if not self.fecha_resolucion:
            return None
        
        delta = self.fecha_resolucion - self.fecha_reporte
        return delta


# ========= Modelo de Respuestas a Incidencias =========
class RespuestaIncidencia(models.Model):
    incidencia = models.ForeignKey(
        'IncidenciaLaboratorio',
        on_delete=models.CASCADE,
        related_name='respuestas',
        help_text="Incidencia a la que pertenece esta respuesta"
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='respuestas_incidencias',
        help_text="Usuario que escribió la respuesta"
    )
    mensaje = models.TextField(
        help_text="Contenido de la respuesta"
    )
    es_resolucion = models.BooleanField(
        default=False,
        help_text="Indica si esta respuesta marca la resolución de la incidencia"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    # Archivos adjuntos en la respuesta
    archivo_adjunto = models.FileField(
        upload_to='incidencias/respuestas/',
        blank=True,
        null=True,
        help_text="Archivo adjunto en la respuesta"
    )
    
    class Meta:
        ordering = ['fecha_creacion']
        verbose_name = "Respuesta de Incidencia"
        verbose_name_plural = "Respuestas de Incidencias"
    
    def __str__(self):
        return f"Respuesta #{self.pk} - {self.incidencia.titulo} - {self.autor}"


# ========= Modelo de Usuarios Asociados (Becarios) =========
class UsuarioAsociado(models.Model):
    """Modelo para gestionar becarios asociados a investigadores principales"""
    
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('suspendido', 'Suspendido'),
    ]
    
    # Investigador principal (usuario DTF registrado)
    investigador_principal = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='becarios_asociados',
        help_text="Usuario DTF responsable del becario externo"
    )
    
    # Datos del becario
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre del becario"
    )
    apellidos = models.CharField(
        max_length=100,
        help_text="Apellidos del becario"
    )
    email = models.EmailField(
        help_text="Email de contacto del becario"
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        help_text="Teléfono de contacto (opcional)"
    )
    
    # Información académica/profesional
    tipo_becario = models.CharField(
        max_length=50,
        choices=[
            ('becario_predoc', 'Becario Predoctoral'),
            ('becario_postdoc', 'Becario Postdoctoral'),
            ('estudiante_tfg', 'Estudiante TFG'),
            ('estudiante_tfm', 'Estudiante TFM'),
            ('investigador_visitante', 'Investigador Visitante'),
            ('otro', 'Otro'),
        ],
        help_text="Tipo de becario o colaborador"
    )
    institucion_origen = models.CharField(
        max_length=200,
        blank=True,
        help_text="Institución de origen del becario"
    )
    
    # Fechas de asociación
    fecha_inicio = models.DateField(
        help_text="Fecha de inicio de la asociación"
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de finalización de la asociación (opcional)"
    )
    
    # Estado y permisos
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activo',
        help_text="Estado actual de la asociación"
    )
    puede_solicitar_autonomo = models.BooleanField(
        default=True,
        help_text="¿Puede el becario realizar solicitudes de forma autónoma?"
    )
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones adicionales sobre el becario"
    )
    
    # Metadatos
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='becarios_creados',
        help_text="Usuario que creó esta asociación"
    )
    
    class Meta:
        ordering = ['-creado_en']
        verbose_name = "Usuario Asociado"
        verbose_name_plural = "Usuarios Asociados"
        unique_together = ['investigador_principal', 'email']
    
    def __str__(self):
        return f"{self.nombre} {self.apellidos} - {self.investigador_principal.get_full_name()}"
    
    @property
    def nombre_completo(self):
        """Retorna el nombre completo del becario"""
        return f"{self.nombre} {self.apellidos}"
    
    @property
    def esta_activo(self):
        """Verifica si la asociación está activa"""
        today = timezone.now().date()
        
        if self.estado != 'activo':
            return False
        
        if self.fecha_fin and self.fecha_fin < today:
            return False
        
        return self.fecha_inicio <= today
    
    def get_estado_display_color(self):
        """Retorna el color CSS para el estado"""
        colors = {
            'activo': '#28a745',
            'inactivo': '#6c757d',
            'suspendido': '#dc3545'
        }
        return colors.get(self.estado, '#6c757d')


# ========= Modelo de Mensajes Internos =========
class MensajeInterno(models.Model):
    """Modelo para mensajes internos entre técnicos y usuarios"""
    
    TIPO_MENSAJE_CHOICES = [
        ('consulta', 'Consulta'),
        ('informacion', 'Información'),
        ('recordatorio', 'Recordatorio'),
        ('urgencia', 'Urgencia'),
        ('general', 'General'),
    ]
    
    # Remitente y destinatario
    remitente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mensajes_enviados',
        help_text="Usuario que envía el mensaje"
    )
    
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mensajes_recibidos',
        help_text="Usuario que recibe el mensaje"
    )
    
    # Contenido del mensaje
    asunto = models.CharField(
        max_length=200,
        help_text="Asunto del mensaje"
    )
    
    contenido = models.TextField(
        help_text="Contenido del mensaje"
    )
    
    # Tipo y estado
    tipo_mensaje = models.CharField(
        max_length=20,
        choices=TIPO_MENSAJE_CHOICES,
        default='general',
        help_text="Tipo de mensaje"
    )
    
    leido = models.BooleanField(
        default=False,
        help_text="¿Ha sido leído el mensaje?"
    )
    
    fecha_leido = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora en que se leyó el mensaje"
    )
    
    # Relación opcional con solicitud
    solicitud = models.ForeignKey(
        'Solicitud',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mensajes',
        help_text="Solicitud relacionada (opcional)"
    )
    
    # Metadatos
    fecha_envio = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_envio']
        verbose_name = "Mensaje Interno"
        verbose_name_plural = "Mensajes Internos"
    
    def __str__(self):
        return f"{self.asunto} - {self.remitente.get_full_name()} → {self.destinatario.get_full_name()}"
    
    def marcar_como_leido(self):
        """Marca el mensaje como leído"""
        if not self.leido:
            self.leido = True
            self.fecha_leido = timezone.now()
            self.save()
    
    def get_tipo_display_color(self):
        """Retorna el color CSS para el tipo de mensaje"""
        colors = {
            'consulta': '#17a2b8',
            'informacion': '#28a745',
            'recordatorio': '#ffc107',
            'urgencia': '#dc3545',
            'general': '#6c757d'
        }
        return colors.get(self.tipo_mensaje, '#6c757d')
    
    @property
    def es_urgente(self):
        """Verifica si el mensaje es urgente"""
        return self.tipo_mensaje == 'urgencia'
    
    @property
    def tiempo_transcurrido(self):
        """Retorna el tiempo transcurrido desde el envío"""
        now = timezone.now()
        diff = now - self.fecha_envio
        
        if diff.days > 0:
            return f"{diff.days} día{'s' if diff.days != 1 else ''}"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hora{'s' if hours != 1 else ''}"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minuto{'s' if minutes != 1 else ''}"
        else:
            return "Hace un momento"


class LabIndicadorCalidad(models.Model):
    """Modelo para almacenar indicadores de calidad del proceso en Sigma Lab"""
    
    # Relación con la solicitud
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name='indicadores')
    
    # Fechas para cálculo de indicadores
    fecha_recepcion = models.DateTimeField(help_text="Fecha de recepción de la muestra")
    fecha_finalizacion_analisis = models.DateTimeField(null=True, blank=True, help_text="Fecha de finalización del análisis")
    fecha_entrega_informe = models.DateTimeField(null=True, blank=True, help_text="Fecha de entrega del informe")
    
    # Indicadores calculados
    i1_tiempo_analisis_dias = models.FloatField(null=True, blank=True, help_text="I1: Tiempo de ejecución del análisis (días)")
    i2_tiempo_entrega_dias = models.FloatField(null=True, blank=True, help_text="I2: Tiempo de entrega del informe (días)")
    
    # Metadatos
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-creado_en']
        verbose_name = "Indicador de Calidad Lab"
        verbose_name_plural = "Indicadores de Calidad Lab"
    
    def __str__(self):
        return f"Indicadores Lab - {self.solicitud.material} ({self.solicitud.id})"
    
    def calcular_i1(self):
        """Calcular I1: Tiempo de ejecución del análisis por muestra"""
        if self.fecha_finalizacion_analisis and self.fecha_recepcion:
            delta = self.fecha_finalizacion_analisis - self.fecha_recepcion
            return delta.total_seconds() / (24 * 3600)  # Convertir a días
        return None
    
    def calcular_i2(self):
        """Calcular I2: Tiempo de entrega del informe desde la finalización del análisis"""
        if self.fecha_entrega_informe and self.fecha_finalizacion_analisis:
            delta = self.fecha_entrega_informe - self.fecha_finalizacion_analisis
            return delta.total_seconds() / (24 * 3600)  # Convertir a días
        return None
    
    def actualizar_indicadores(self):
        """Actualizar los indicadores calculados"""
        self.i1_tiempo_analisis_dias = self.calcular_i1()
        self.i2_tiempo_entrega_dias = self.calcular_i2()
        self.save()
    
    @classmethod
    def obtener_promedio_i1(cls):
        """Obtener el promedio de I1 para todas las solicitudes"""
        indicadores = cls.objects.filter(i1_tiempo_analisis_dias__isnull=False)
        if indicadores.exists():
            return sum(ind.i1_tiempo_analisis_dias for ind in indicadores) / indicadores.count()
        return None
    
    @classmethod
    def obtener_promedio_i2(cls):
        """Obtener el promedio de I2 para todas las solicitudes"""
        indicadores = cls.objects.filter(i2_tiempo_entrega_dias__isnull=False)
        if indicadores.exists():
            return sum(ind.i2_tiempo_entrega_dias for ind in indicadores) / indicadores.count()
        return None


# ========= SISTEMA DE EQUIPOS DEL LABORATORIO =========

class EquipoLaboratorio(models.Model):
    """Modelo para gestionar equipos que pueden ser sacados del laboratorio"""
    
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('prestado', 'Prestado'),
        ('mantenimiento', 'En Mantenimiento'),
        ('deshabilitado', 'Deshabilitado'),
    ]
    
    CATEGORIA_CHOICES = [
        ('herramientas', 'Herramientas'),
        ('instrumentos', 'Instrumentos de Medición'),
        ('equipos_electronicos', 'Equipos Electrónicos'),
        ('materiales', 'Materiales'),
        ('otros', 'Otros'),
    ]
    
    # Información básica del equipo
    nombre = models.CharField(
        max_length=200,
        help_text="Nombre del equipo"
    )
    codigo = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código único del equipo"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción detallada del equipo"
    )
    categoria = models.CharField(
        max_length=30,
        choices=CATEGORIA_CHOICES,
        help_text="Categoría del equipo"
    )
    
    # Estado y disponibilidad
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='disponible',
        help_text="Estado actual del equipo"
    )
    disponible_para_prestamo = models.BooleanField(
        default=True,
        help_text="¿Está disponible para préstamo?"
    )
    
    # Ubicación
    ubicacion_laboratorio = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ubicación dentro del laboratorio"
    )
    
    # Información de mantenimiento
    requiere_mantenimiento = models.BooleanField(
        default=False,
        help_text="¿Requiere mantenimiento especial?"
    )
    instrucciones_uso = models.TextField(
        blank=True,
        help_text="Instrucciones de uso y manejo"
    )
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones adicionales"
    )
    
    # Metadatos
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='equipos_creados',
        help_text="Técnico que creó el registro del equipo"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['nombre']
        verbose_name = "Equipo del Laboratorio"
        verbose_name_plural = "Equipos del Laboratorio"
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    @property
    def esta_disponible(self):
        """Verifica si el equipo está disponible para préstamo"""
        return (
            self.estado == 'disponible' and 
            self.disponible_para_prestamo and
            not self.prestamos_activos.exists()
        )
    
    @property
    def prestamos_activos(self):
        """Retorna los préstamos activos de este equipo"""
        return self.prestamos.filter(estado='activo')
    
    def get_estado_color(self):
        """Retorna el color CSS para el estado"""
        colors = {
            'disponible': '#28a745',
            'prestado': '#ffc107',
            'mantenimiento': '#17a2b8',
            'deshabilitado': '#dc3545'
        }
        return colors.get(self.estado, '#6c757d')


class PrestamoEquipo(models.Model):
    """Modelo para gestionar préstamos de equipos"""
    
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('devuelto', 'Devuelto'),
        ('vencido', 'Vencido'),
        ('perdido', 'Perdido'),
    ]
    
    # Relaciones
    equipo = models.ForeignKey(
        'EquipoLaboratorio',
        on_delete=models.CASCADE,
        related_name='prestamos',
        help_text="Equipo prestado"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prestamos_realizados',
        help_text="Usuario que solicita el préstamo"
    )
    tecnico_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prestamos_gestionados',
        help_text="Técnico responsable del laboratorio"
    )
    
    # Información del préstamo
    fecha_prestamo = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora del préstamo"
    )
    fecha_devolucion_estimada = models.DateTimeField(
        help_text="Fecha estimada de devolución"
    )
    fecha_devolucion_real = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha real de devolución"
    )
    dias_prestamo = models.PositiveIntegerField(
        help_text="Número de días de préstamo"
    )
    
    # Estado y seguimiento
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activo',
        help_text="Estado del préstamo"
    )
    
    # Información adicional
    proposito_uso = models.TextField(
        blank=True,
        help_text="Propósito del uso del equipo"
    )
    observaciones_prestamo = models.TextField(
        blank=True,
        help_text="Observaciones del préstamo"
    )
    observaciones_devolucion = models.TextField(
        blank=True,
        help_text="Observaciones de la devolución"
    )
    
    # Notificaciones
    notificacion_enviada_vencimiento = models.BooleanField(
        default=False,
        help_text="¿Se envió notificación de vencimiento?"
    )
    notificacion_enviada_retraso = models.BooleanField(
        default=False,
        help_text="¿Se envió notificación de retraso?"
    )
    
    class Meta:
        ordering = ['-fecha_prestamo']
        verbose_name = "Préstamo de Equipo"
        verbose_name_plural = "Préstamos de Equipos"
    
    def __str__(self):
        return f"Préstamo {self.equipo.codigo} - {self.usuario.get_full_name()}"
    
    @property
    def esta_vencido(self):
        """Verifica si el préstamo está vencido"""
        if self.estado != 'activo':
            return False
        return timezone.now() > self.fecha_devolucion_estimada
    
    @property
    def dias_vencido(self):
        """Calcula los días de retraso si está vencido"""
        if not self.esta_vencido:
            return 0
        delta = timezone.now() - self.fecha_devolucion_estimada
        return delta.days
    
    @property
    def dias_restantes(self):
        """Calcula los días restantes para la devolución"""
        if self.estado != 'activo':
            return 0
        delta = self.fecha_devolucion_estimada - timezone.now()
        return max(0, delta.days)
    
    def marcar_como_devuelto(self, observaciones=""):
        """Marca el préstamo como devuelto"""
        self.estado = 'devuelto'
        self.fecha_devolucion_real = timezone.now()
        self.observaciones_devolucion = observaciones
        self.save()
        
        # Actualizar estado del equipo
        self.equipo.estado = 'disponible'
        self.equipo.save()
    
    def marcar_como_vencido(self):
        """Marca el préstamo como vencido"""
        self.estado = 'vencido'
        self.save()
    
    def get_estado_color(self):
        """Retorna el color CSS para el estado"""
        colors = {
            'activo': '#28a745',
            'devuelto': '#6c757d',
            'vencido': '#dc3545',
            'perdido': '#fd7e14'
        }
        return colors.get(self.estado, '#6c757d')


class NotificacionPrestamo(models.Model):
    """Modelo para gestionar notificaciones de préstamos"""
    
    TIPO_CHOICES = [
        ('prestamo_realizado', 'Préstamo Realizado'),
        ('recordatorio_vencimiento', 'Recordatorio de Vencimiento'),
        ('equipo_vencido', 'Equipo Vencido'),
        ('equipo_devuelto', 'Equipo Devuelto'),
    ]
    
    prestamo = models.ForeignKey(
        'PrestamoEquipo',
        on_delete=models.CASCADE,
        related_name='notificaciones',
        help_text="Préstamo relacionado"
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones_prestamos',
        help_text="Usuario que recibe la notificación"
    )
    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES,
        help_text="Tipo de notificación"
    )
    mensaje = models.TextField(
        help_text="Contenido de la notificación"
    )
    enviada = models.BooleanField(
        default=False,
        help_text="¿Fue enviada la notificación?"
    )
    fecha_envio = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de envío de la notificación"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Notificación de Préstamo"
        verbose_name_plural = "Notificaciones de Préstamos"
    
    def __str__(self):
        return f"Notificación {self.get_tipo_display()} - {self.destinatario.get_full_name()}"
    
    def marcar_como_enviada(self):
        """Marca la notificación como enviada"""
        self.enviada = True
        self.fecha_envio = timezone.now()
        self.save()
