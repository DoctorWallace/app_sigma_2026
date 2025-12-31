from django.db import models
from django.conf import settings


class MecSample(models.Model):
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=100, blank=True)
    tratamientos = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.nombre}"


class MecSolicitud(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ACEPTADA = "aceptada", "Aceptada"
        RECHAZADA = "rechazada", "Rechazada"
        EN_CURSO = "en_curso", "En curso"
        FINALIZADA = "finalizada", "Finalizada"

    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="mec_solicitudes")
    tecnico_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="mec_solicitudes_asignadas"
    )

    # Datos generales
    material = models.CharField(max_length=200, blank=True)
    procedencia = models.CharField(max_length=200, blank=True)
    numero_muestras = models.PositiveIntegerField(default=1)
    tratamientos = models.TextField(blank=True)

    # Ensayo de dureza
    ensayo_dureza = models.BooleanField(default=False)
    dureza_carga = models.CharField(max_length=100, blank=True)
    dureza_huellas_filas = models.PositiveIntegerField(null=True, blank=True)
    dureza_huellas_columnas = models.PositiveIntegerField(null=True, blank=True)

    # Ensayo de tracción
    ensayo_traccion = models.BooleanField(default=False)
    traccion_temperatura = models.CharField(max_length=200, blank=True, help_text="Una por muestra, separadas por coma o línea")
    traccion_velocidad_deformacion = models.FloatField(null=True, blank=True, help_text="s^-1")
    traccion_diametro = models.FloatField(null=True, blank=True)
    traccion_longitud_marca = models.FloatField(null=True, blank=True)

    # Ensayo de fatiga
    ensayo_fatiga = models.BooleanField(default=False)
    fatiga_temperatura = models.FloatField(null=True, blank=True)
    fatiga_porcentaje_deformacion = models.FloatField(null=True, blank=True)
    fatiga_frecuencia = models.FloatField(null=True, blank=True)
    fatiga_eps_max = models.FloatField(null=True, blank=True)
    fatiga_eps_min = models.FloatField(null=True, blank=True)

    # Ensayo de creep-fatiga
    ensayo_creep_fatiga = models.BooleanField(default=False)
    creep_temperatura = models.FloatField(null=True, blank=True)
    creep_porcentaje_deformacion = models.FloatField(null=True, blank=True)
    creep_frecuencia = models.FloatField(null=True, blank=True)
    creep_eps_max = models.FloatField(null=True, blank=True)
    creep_eps_min = models.FloatField(null=True, blank=True)
    creep_mantenimiento_tipo = models.CharField(max_length=20, blank=True, help_text="carga/deformacion")
    creep_mantenimiento_en = models.CharField(max_length=20, blank=True, help_text="maxima/minima")
    creep_tiempo_mantenimiento_s = models.FloatField(null=True, blank=True)

    observaciones = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"MEC#{self.pk or '-'} - {self.solicitante} - {self.estado}"


class MecMuestraNombre(models.Model):
    solicitud = models.ForeignKey(MecSolicitud, on_delete=models.CASCADE, related_name="nombres")
    nombre = models.CharField(max_length=200)

    def __str__(self):
        return self.nombre


class MecEvento(models.Model):
    """Entrada de diario (evento) asociada a una solicitud MEC."""
    solicitud = models.ForeignKey(MecSolicitud, on_delete=models.CASCADE, related_name="eventos")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    texto = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en", "-id"]

    def __str__(self):
        return f"Evento MEC#{self.solicitud_id} por {self.autor}: {self.texto[:30]}"


class MecNecesidad(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha = models.DateField()
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return self.titulo


class MecMensaje(models.Model):
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    asunto = models.CharField(max_length=200)
    mensaje = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en", "-id"]

    def __str__(self):
        return self.asunto


class MecIndicadorCalidad(models.Model):
    """Modelo para almacenar indicadores de calidad del proceso en Sigma MEC"""
    
    # Relación con la solicitud
    solicitud = models.ForeignKey(MecSolicitud, on_delete=models.CASCADE, related_name='indicadores')
    
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
        verbose_name = "Indicador de Calidad MEC"
        verbose_name_plural = "Indicadores de Calidad MEC"
    
    def __str__(self):
        return f"Indicadores MEC - {self.solicitud.material} ({self.solicitud.id})"
    
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
