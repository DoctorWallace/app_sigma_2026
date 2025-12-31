from django.db import models
from django.conf import settings
from django.utils import timezone


class OpticsSample(models.Model):
    """Modelo para muestras de análisis óptico"""
    nombre = models.CharField(max_length=200, help_text="Nombre de la muestra")
    tipo = models.CharField(max_length=100, blank=True, help_text="Tipo de material")
    tratamientos = models.TextField(blank=True, help_text="Tratamientos previos")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.nombre}"


class OpticsSolicitud(models.Model):
    """Modelo para solicitudes de análisis óptico"""
    
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ACEPTADA = "aceptada", "Aceptada"
        RECHAZADA = "rechazada", "Rechazada"
        EN_CURSO = "en_curso", "En curso"
        FINALIZADA = "finalizada", "Finalizada"

    class TipoMedida(models.TextChoices):
        UV_VIS = "uv_vis", "UV – VIS"
        FTIR = "ftir", "FTIR"

    class FormatoResultado(models.TextChoices):
        IMAGEN = "imagen", "Imagen"
        ARCHIVO_TEXTO = "archivo_texto", "Archivo de texto"
        AMBOS = "ambos", "Ambos"

    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="optics_solicitudes"
    )
    tecnico_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name="optics_solicitudes_asignadas"
    )

    # Datos generales
    material = models.CharField(max_length=200, help_text="Material")
    numero_muestras = models.PositiveIntegerField(default=1, help_text="Nº muestras")
    referencia_muestras = models.CharField(max_length=200, blank=True, help_text="Ref. muestras")
    
    # Tamaño de muestra (diámetro o lados en cm)
    diametro_muestra = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Diámetro de la muestra en cm"
    )
    lado1_muestra = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Lado 1 de la muestra en cm"
    )
    lado2_muestra = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Lado 2 de la muestra en cm"
    )
    tipo_tamano = models.CharField(
        max_length=10,
        choices=[
            ('diametro', 'Diámetro'),
            ('lados', 'Lados')
        ],
        default='diametro',
        help_text="Tipo de medida de tamaño"
    )
    
    # Medidas a realizar
    medidas_realizar = models.CharField(
        max_length=10,
        choices=TipoMedida.choices,
        help_text="Medidas a realizar"
    )
    
    # Formato de resultados
    formato_resultado = models.CharField(
        max_length=15,
        choices=FormatoResultado.choices,
        default=FormatoResultado.AMBOS,
        help_text="Formato de resultados deseados"
    )
    
    # Información adicional
    otros_datos = models.TextField(
        blank=True,
        help_text="Otros datos de interés o información relevante de la/s muestra/s"
    )
    
    # Estado y fechas
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    aceptado_en = models.DateTimeField(null=True, blank=True)
    finalizado_en = models.DateTimeField(null=True, blank=True)
    
    # Código de análisis (generado por el técnico)
    codigo_analisis = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Código generado automáticamente (ej: 2025-01)"
    )

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Solicitud Óptica"
        verbose_name_plural = "Solicitudes Ópticas"

    def __str__(self):
        return f"OPT-{self.id} - {self.material}"

    def save(self, *args, **kwargs):
        if not self.codigo_analisis and self.estado == self.Estado.ACEPTADA:
            self.codigo_analisis = self.generar_codigo_analisis()
        super().save(*args, **kwargs)

    def generar_codigo_analisis(self):
        """Genera código de análisis: año-número correlativo"""
        year = timezone.now().year
        # Contar solicitudes aceptadas del mismo año
        existing_count = OpticsSolicitud.objects.filter(
            estado=self.Estado.ACEPTADA,
            creado_en__year=year
        ).count()
        return f"{year}-{existing_count + 1:02d}"


class OpticsMuestra(models.Model):
    """Modelo para muestras individuales de análisis óptico"""
    solicitud = models.ForeignKey(
        OpticsSolicitud,
        on_delete=models.CASCADE,
        related_name="muestras"
    )
    numero_secuencia = models.PositiveIntegerField(help_text="Número de secuencia")
    identificacion = models.CharField(max_length=200, help_text="Identificación de la muestra")
    descripcion = models.TextField(blank=True, help_text="Descripción de la muestra")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["numero_secuencia"]
        unique_together = ["solicitud", "numero_secuencia"]

    def __str__(self):
        return f"{self.solicitud} - Muestra {self.numero_secuencia}"


class OpticsResultado(models.Model):
    """Modelo para resultados de análisis óptico"""
    solicitud = models.ForeignKey(
        OpticsSolicitud,
        on_delete=models.CASCADE,
        related_name="resultados"
    )
    codigo_informe = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código del informe (PT-DTF-07-F03-CODIGO_ANALISIS)"
    )
    archivo_resultado = models.FileField(
        upload_to="optics/resultados/",
        help_text="Archivo de resultados"
    )
    observaciones = models.TextField(blank=True, help_text="Observaciones del técnico")
    creado_en = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="optics_resultados_creados"
    )

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Resultado {self.codigo_informe}"


class OpticsAnalisisDatos(models.Model):
    """Análisis de datos ópticos con representación gráfica"""
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
    tecnico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="optics_analisis")
    solicitud = models.ForeignKey(
        OpticsSolicitud,
        on_delete=models.CASCADE,
        related_name="analisis_datos",
        null=True,
        blank=True,
        help_text="Solicitud óptica asociada"
    )
    
    # Archivos de entrada
    archivo_datos = models.FileField(
        upload_to="optics_analisis/datos/",
        help_text="Archivo de datos original"
    )
    tipo_archivo = models.CharField(max_length=10, choices=TipoArchivo.choices, default=TipoArchivo.TXT)
    
    # Configuración del análisis
    separador = models.CharField(max_length=10, default="\t", help_text="Separador de columnas")
    decimal = models.CharField(max_length=5, default=",", help_text="Separador decimal")
    codificacion = models.CharField(max_length=20, default="cp1252", help_text="Codificación del archivo")
    
    # Opciones de representación
    mostrar_espectro = models.BooleanField(default=True, help_text="Mostrar gráfica de espectro")
    mostrar_transmitancia = models.BooleanField(default=True, help_text="Mostrar gráfica de transmitancia")
    mostrar_absorbancia = models.BooleanField(default=True, help_text="Mostrar gráfica de absorbancia")
    mostrar_overview = models.BooleanField(default=True, help_text="Mostrar gráfica general")
    
    # Archivos generados
    archivo_csv_limpio = models.FileField(upload_to="optics_analisis/csv/", blank=True, null=True)
    archivo_espectro = models.FileField(upload_to="optics_analisis/graficas/", blank=True, null=True)
    archivo_transmitancia = models.FileField(upload_to="optics_analisis/graficas/", blank=True, null=True)
    archivo_absorbancia = models.FileField(upload_to="optics_analisis/graficas/", blank=True, null=True)
    archivo_overview = models.FileField(upload_to="optics_analisis/graficas/", blank=True, null=True)
    
    # Estadísticas del análisis
    duracion_minutos = models.FloatField(null=True, blank=True, help_text="Duración del análisis en minutos")
    num_muestras = models.IntegerField(null=True, blank=True, help_text="Número de muestras procesadas")
    columnas_detectadas = models.TextField(blank=True, help_text="Columnas detectadas en el archivo")
    
    # Estado y fechas
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PROCESANDO)
    creado_en = models.DateTimeField(auto_now_add=True)
    procesado_en = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Análisis de Datos Ópticos"
        verbose_name_plural = "Análisis de Datos Ópticos"
        ordering = ['-creado_en']
    
    def __str__(self):
        return f"Análisis {self.nombre} - {self.estado}"
