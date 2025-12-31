from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from icts.models import AccessProposal

User = get_user_model()


class SEMAnalysis(models.Model):
    """Modelo para registrar análisis SEM/FIB"""
    
    ANALYSIS_TYPE_CHOICES = [
        ('sem', 'SEM'),
        ('fib', 'FIB'),
    ]
    
    # Relación con la propuesta ICTS
    access_proposal = models.ForeignKey(
        AccessProposal,
        on_delete=models.CASCADE,
        related_name='sem_analyses',
        help_text="Propuesta ICTS asociada"
    )
    
    # Información del análisis
    analysis_type = models.CharField(
        max_length=3,
        choices=ANALYSIS_TYPE_CHOICES,
        help_text="Tipo de análisis: SEM o FIB"
    )
    
    # Número de registro (ej: 25-SEM-01)
    registration_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Número de registro único"
    )
    
    # Información de las muestras (JSON para múltiples muestras)
    samples_data = models.JSONField(
        default=list,
        help_text="Lista de muestras asociadas al análisis"
    )
    
    # Fechas
    analysis_date = models.DateField(
        help_text="Fecha del análisis"
    )
    
    completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de finalización"
    )
    
    # Personas involucradas
    client = models.CharField(
        max_length=200,
        help_text="Nombre del cliente (solicitante)"
    )
    
    technician = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sem_analyses_conducted',
        help_text="Técnico responsable"
    )
    
    # Características y observaciones
    sample_characteristics = models.TextField(
        blank=True,
        help_text="Características de la muestra"
    )
    
    client_requirements = models.TextField(
        blank=True,
        help_text="Requerimientos del cliente"
    )
    
    observations = models.TextField(
        blank=True,
        help_text="Observaciones del técnico"
    )
    
    # Comentarios durante la sesión
    session_comments = models.TextField(
        blank=True,
        help_text="Comentarios y observaciones durante la sesión"
    )
    
    # Estado de la sesión
    session_status = models.CharField(
        max_length=20,
        choices=[
            ('in_progress', 'En Progreso'),
            ('completed', 'Completada'),
        ],
        default='in_progress',
        help_text="Estado de la sesión de análisis"
    )
    
    # Informe
    report_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Código del informe (IN-SEM-XX-XXX)"
    )
    
    report_files = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de archivos del informe"
    )
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Análisis SEM/FIB"
        verbose_name_plural = "Análisis SEM/FIB"
        ordering = ['-analysis_date', '-created_at']
    
    def __str__(self):
        sample_count = len(self.samples_data) if self.samples_data else 0
        return f"{self.registration_number} - {sample_count} muestra(s) ({self.get_analysis_type_display()})"
    
    @property
    def sample_names(self):
        """Retorna los nombres de las muestras como string"""
        if not self.samples_data:
            return "Sin muestras"
        return ", ".join([sample.get('name', 'Sin nombre') for sample in self.samples_data])
    
    def save(self, *args, **kwargs):
        if not self.registration_number:
            self.registration_number = self.generate_registration_number()
        if not self.report_code:
            self.report_code = self.generate_report_code()
        super().save(*args, **kwargs)
    
    def generate_registration_number(self):
        """Genera número de registro: 25-SEM-01"""
        year = self.analysis_date.year % 100  # Últimos 2 dígitos del año
        analysis_prefix = self.analysis_type.upper()
        
        # Contar análisis existentes del mismo tipo y año
        existing_count = SEMAnalysis.objects.filter(
            analysis_type=self.analysis_type,
            analysis_date__year=self.analysis_date.year
        ).count()
        
        number = existing_count + 1
        return f"{year:02d}-{analysis_prefix}-{number:02d}"
    
    def generate_report_code(self):
        """Genera código de informe: IN-SEM-25-001 o IN-FIB-25-001"""
        year = self.analysis_date.year % 100  # Últimos 2 dígitos del año
        analysis_prefix = self.analysis_type.upper()
        
        # Contar informes existentes del mismo tipo y año
        existing_count = SEMAnalysis.objects.filter(
            analysis_type=self.analysis_type,
            analysis_date__year=self.analysis_date.year,
            report_code__startswith=f'IN-{analysis_prefix}-{year:02d}-'
        ).count()
        
        number = existing_count + 1
        return f"IN-{analysis_prefix}-{year:02d}-{number:03d}"


class SEMSample(models.Model):
    """Modelo para muestras adicionales que pueden agregar los técnicos"""
    
    analysis = models.ForeignKey(
        SEMAnalysis,
        on_delete=models.CASCADE,
        related_name='additional_samples',
        help_text="Análisis asociado"
    )
    
    identification = models.CharField(
        max_length=200,
        help_text="Identificación de la muestra"
    )
    
    name = models.CharField(
        max_length=200,
        help_text="Nombre de la muestra"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Descripción de la muestra"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Muestra SEM/FIB"
        verbose_name_plural = "Muestras SEM/FIB"
    
    def __str__(self):
        return f"{self.identification} - {self.name}"
