from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.conf import settings


class DpSample(models.Model):
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=100, blank=True)
    tratamientos = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.nombre}"


class DpSolicitud(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ACEPTADA = "aceptada", "Aceptada"
        RECHAZADA = "rechazada", "Rechazada"
        EN_CURSO = "en_curso", "En curso"
        FINALIZADA = "finalizada", "Finalizada"

    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="dp_solicitudes")
    tecnico_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="dp_solicitudes_asignadas"
    )

    # Datos generales
    material = models.CharField(max_length=200, blank=True)
    procedencia = models.CharField(max_length=200, blank=True)
    numero_muestras = models.PositiveIntegerField(default=1)
    tratamientos = models.TextField(blank=True)

    # Ensayo de desorción
    ensayo_desorcion = models.BooleanField(default=False)
    desorcion_temperatura = models.FloatField(null=True, blank=True, help_text="Temperatura en °C")
    desorcion_tiempo = models.FloatField(null=True, blank=True, help_text="Tiempo en horas")
    desorcion_presion = models.FloatField(null=True, blank=True, help_text="Presión en bar")
    desorcion_gas = models.CharField(max_length=100, blank=True, help_text="Gas utilizado (H2, D2, etc.)")
    desorcion_volumen_muestra = models.FloatField(null=True, blank=True, help_text="Volumen de muestra en cm³")

    # Ensayo de permeación
    ensayo_permeacion = models.BooleanField(default=False)
    permeacion_temperatura = models.FloatField(null=True, blank=True, help_text="Temperatura en °C")
    permeacion_presion_alta = models.FloatField(null=True, blank=True, help_text="Presión lado alto en bar")
    permeacion_presion_baja = models.FloatField(null=True, blank=True, help_text="Presión lado bajo en bar")
    permeacion_gas = models.CharField(max_length=100, blank=True, help_text="Gas utilizado (H2, D2, etc.)")
    permeacion_espesor_membrana = models.FloatField(null=True, blank=True, help_text="Espesor de membrana en mm")
    permeacion_area_membrana = models.FloatField(null=True, blank=True, help_text="Área de membrana en cm²")

    # Ensayo de difusión
    ensayo_difusion = models.BooleanField(default=False)
    difusion_temperatura = models.FloatField(null=True, blank=True, help_text="Temperatura en °C")
    difusion_tiempo = models.FloatField(null=True, blank=True, help_text="Tiempo en horas")
    difusion_concentracion_inicial = models.FloatField(null=True, blank=True, help_text="Concentración inicial en ppm")
    difusion_concentracion_final = models.FloatField(null=True, blank=True, help_text="Concentración final en ppm")
    difusion_volumen_solucion = models.FloatField(null=True, blank=True, help_text="Volumen de solución en ml")

    # Ensayo de adsorción
    ensayo_adsorcion = models.BooleanField(default=False)
    adsorcion_temperatura = models.FloatField(null=True, blank=True, help_text="Temperatura en °C")
    adsorcion_presion = models.FloatField(null=True, blank=True, help_text="Presión en bar")
    adsorcion_gas = models.CharField(max_length=100, blank=True, help_text="Gas utilizado")
    adsorcion_masa_muestra = models.FloatField(null=True, blank=True, help_text="Masa de muestra en mg")
    adsorcion_area_superficie = models.FloatField(null=True, blank=True, help_text="Área superficial en m²/g")

    observaciones = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"DP#{self.pk or '-'} - {self.solicitante} - {self.estado}"


class DpMuestraNombre(models.Model):
    solicitud = models.ForeignKey(DpSolicitud, on_delete=models.CASCADE, related_name="nombres")
    nombre = models.CharField(max_length=200)

    def __str__(self):
        return self.nombre


class DpEvento(models.Model):
    """Entrada de diario (evento) asociada a una solicitud DP."""
    solicitud = models.ForeignKey(DpSolicitud, on_delete=models.CASCADE, related_name="eventos")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    texto = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en", "-id"]

    def __str__(self):
        return f"Evento DP#{self.solicitud_id} por {self.autor}: {self.texto[:30]}"


class DpNecesidad(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha = models.DateField()
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return self.titulo


class DpMensaje(models.Model):
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    asunto = models.CharField(max_length=200)
    mensaje = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en", "-id"]

    def __str__(self):
        return self.asunto


class DpSolicitudTermica(models.Model):
    """Solicitud específica para análisis térmico DP"""
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ACEPTADA = "aceptada", "Aceptada"
        RECHAZADA = "rechazada", "Rechazada"
        EN_CURSO = "en_curso", "En curso"
        FINALIZADA = "finalizada", "Finalizada"

    class MasaChoices(models.TextChoices):
        MASA_2 = "2", "Masa 2 uma"
        MASA_3 = "3", "Masa 3 uma"
        MASA_4 = "4", "Masa 4 uma"

    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="dp_solicitudes_termicas")
    tecnico_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="dp_solicitudes_termicas_asignadas"
    )
    
    # Campos específicos del análisis térmico
    nombre_muestra = models.CharField(max_length=200, help_text="Nombre de la muestra")
    material = models.CharField(max_length=200, help_text="Material de la muestra")
    temperatura_maxima = models.FloatField(
        help_text="Temperatura máxima del ensayo [ºC]",
        validators=[MaxValueValidator(900, "La temperatura máxima no puede superar 900ºC")]
    )
    tasa_calentamiento = models.FloatField(
        help_text="Tasa de calentamiento [ºC/min]",
        validators=[MaxValueValidator(15, "La tasa de calentamiento no puede superar 15ºC/min")]
    )
    tasa_enfriamiento = models.FloatField(
        help_text="Tasa de enfriamiento [ºC/min]",
        validators=[MaxValueValidator(15, "La tasa de enfriamiento no puede superar 15ºC/min")]
    )
    tiempo_permanencia = models.FloatField(
        help_text="Tiempo de permanencia en la temperatura máxima [min]"
    )
    masa_registrar = models.CharField(
        max_length=1,
        choices=MasaChoices.choices,
        help_text="Masa a registrar [uma]"
    )
    
    # Especificaciones de la muestra
    espesor_muestra = models.FloatField(
        help_text="Espesor de la muestra [mm]",
        validators=[
            MinValueValidator(0.1, "El espesor mínimo es 0.1 mm"),
            MaxValueValidator(10, "El espesor máximo es 10 mm")
        ]
    )
    tamaño_muestra = models.FloatField(
        help_text="Tamaño de la muestra [cm²]",
        validators=[MinValueValidator(0.5, "El tamaño mínimo es 0.5 cm²")]
    )
    geometria_muestra = models.CharField(
        max_length=100,
        help_text="Geometría de la muestra (circular, cuadrada, etc.)"
    )
    
    # Campos de control
    observaciones = models.TextField(blank=True, help_text="Observaciones adicionales")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    
    # Fechas
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    fecha_aceptacion = models.DateTimeField(null=True, blank=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Solicitud Térmica DP"
        verbose_name_plural = "Solicitudes Térmicas DP"

    def __str__(self):
        return f"DP-T#{self.pk or '-'} - {self.nombre_muestra} - {self.estado}"

    def puede_ser_aceptada(self):
        return self.estado == self.Estado.PENDIENTE

    def puede_ser_finalizada(self):
        return self.estado == self.Estado.EN_CURSO


class DpResultadoTermico(models.Model):
    """Resultados de análisis térmico"""
    solicitud = models.OneToOneField(DpSolicitudTermica, on_delete=models.CASCADE, related_name="resultado")
    tecnico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    
    # Archivos de resultados
    archivo_resultado = models.FileField(
        upload_to="dp_resultados/",
        help_text="Archivo de resultados (txt o csv)"
    )
    archivo_resultado_2 = models.FileField(
        upload_to="dp_resultados/",
        blank=True,
        null=True,
        help_text="Archivo de resultados adicional (opcional)"
    )
    
    # Metadatos
    fecha_ensayo = models.DateTimeField(help_text="Fecha y hora del ensayo")
    observaciones_tecnico = models.TextField(blank=True, help_text="Observaciones del técnico")
    
    # Control
    creado_en = models.DateTimeField(auto_now_add=True)
    enviado_por_email = models.BooleanField(default=False)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Resultado Térmico DP"
        verbose_name_plural = "Resultados Térmicos DP"

    def __str__(self):
        return f"Resultado DP-T#{self.solicitud_id} - {self.fecha_ensayo}"


class DpAnalisisDatos(models.Model):
    """Análisis de datos térmicos con representación gráfica"""
    class TipoArchivo(models.TextChoices):
        TXT = "txt", "Archivo de texto (.txt)"
        CSV = "csv", "Archivo CSV (.csv)"
        TSV = "tsv", "Archivo TSV (.tsv)"
        DAT = "dat", "Archivo de datos (.dat)"
    
    class Estado(models.TextChoices):
        PROCESANDO = "procesando", "Procesando"
        COMPLETADO = "completado", "Completado"
        ERROR = "error", "Error"
    
    # Metadatos
    nombre = models.CharField(max_length=200, help_text="Nombre del análisis")
    descripcion = models.TextField(blank=True, help_text="Descripción del análisis")
    tecnico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="dp_analisis")
    solicitud_termica = models.ForeignKey(
        DpSolicitudTermica,
        on_delete=models.CASCADE,
        related_name="analisis_datos",
        null=True,
        blank=True,
        help_text="Solicitud termica asociada"
    )
    
    # Archivos de entrada
    archivo_datos = models.FileField(
        upload_to="dp_analisis/datos/",
        help_text="Archivo de datos original"
    )
    tipo_archivo = models.CharField(max_length=10, choices=TipoArchivo.choices, default=TipoArchivo.TXT)
    
    # Configuración del análisis
    separador = models.CharField(max_length=10, default="\t", help_text="Separador de columnas")
    decimal = models.CharField(max_length=5, default=",", help_text="Separador decimal")
    codificacion = models.CharField(max_length=20, default="cp1252", help_text="Codificación del archivo")
    
    # Opciones de representación
    mostrar_temperatura = models.BooleanField(default=True, help_text="Mostrar gráfica de temperatura")
    mostrar_leak = models.BooleanField(default=True, help_text="Mostrar gráfica de leak rate")
    mostrar_heater = models.BooleanField(default=True, help_text="Mostrar gráfica de tensión del calefactor")
    mostrar_overview = models.BooleanField(default=True, help_text="Mostrar panel overview")
    
    # Archivos de salida
    archivo_csv_limpio = models.FileField(
        upload_to="dp_analisis/csv/",
        blank=True,
        null=True,
        help_text="CSV limpio generado"
    )
    archivo_temperatura = models.FileField(
        upload_to="dp_analisis/graficas/",
        blank=True,
        null=True,
        help_text="Gráfica de temperatura (PNG)"
    )
    archivo_leak = models.FileField(
        upload_to="dp_analisis/graficas/",
        blank=True,
        null=True,
        help_text="Gráfica de leak rate (PNG)"
    )
    archivo_heater = models.FileField(
        upload_to="dp_analisis/graficas/",
        blank=True,
        null=True,
        help_text="Gráfica de tensión del calefactor (PNG)"
    )
    archivo_overview = models.FileField(
        upload_to="dp_analisis/graficas/",
        blank=True,
        null=True,
        help_text="Panel overview (PNG)"
    )
    
    # Estado y control
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PROCESANDO)
    mensaje_error = models.TextField(blank=True, help_text="Mensaje de error si el procesamiento falla")
    
    # Estadísticas del análisis
    duracion_minutos = models.FloatField(null=True, blank=True, help_text="Duración del ensayo en minutos")
    num_muestras = models.IntegerField(null=True, blank=True, help_text="Número de muestras")
    columnas_detectadas = models.TextField(blank=True, help_text="Columnas detectadas en el archivo")
    
    # Fechas
    creado_en = models.DateTimeField(auto_now_add=True)
    procesado_en = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Análisis de Datos DP"
        verbose_name_plural = "Análisis de Datos DP"
    
    def __str__(self):
        return f"Análisis #{self.pk} - {self.nombre} ({self.estado})"
    
    def get_graficas_disponibles(self):
        """Retorna las gráficas que están disponibles"""
        graficas = []
        if self.archivo_temperatura:
            graficas.append(('temperatura', 'Temperatura', self.archivo_temperatura.url))
        if self.archivo_leak:
            graficas.append(('leak', 'Leak Rate', self.archivo_leak.url))
        if self.archivo_heater:
            graficas.append(('heater', 'Tensión Calefactor', self.archivo_heater.url))
        if self.archivo_overview:
            graficas.append(('overview', 'Panel Overview', self.archivo_overview.url))
        return graficas


class DpIndicadorCalidad(models.Model):
    """Modelo para almacenar indicadores de calidad del proceso"""
    
    # Relación con la solicitud
    solicitud = models.ForeignKey(DpSolicitud, on_delete=models.CASCADE, related_name='indicadores')
    
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
        verbose_name = "Indicador de Calidad"
        verbose_name_plural = "Indicadores de Calidad"
    
    def __str__(self):
        return f"Indicadores - {self.solicitud.material} ({self.solicitud.id})"
    
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

