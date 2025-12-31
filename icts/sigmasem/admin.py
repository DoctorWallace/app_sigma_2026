from django.contrib import admin
from .models import SEMAnalysis, SEMSample


@admin.register(SEMAnalysis)
class SEMAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'registration_number',
        'analysis_type',
        'sample_names',
        'client',
        'technician',
        'analysis_date',
        'session_status',
        'report_code'
    ]
    list_filter = [
        'analysis_type',
        'analysis_date',
        'session_status',
        'technician'
    ]
    search_fields = [
        'registration_number',
        'client',
        'report_code'
    ]
    readonly_fields = [
        'registration_number',
        'report_code',
        'created_at',
        'updated_at'
    ]
    fieldsets = (
        ('Información del Análisis', {
            'fields': (
                'access_proposal',
                'analysis_type',
                'registration_number',
                'report_code'
            )
        }),
        ('Muestras', {
            'fields': (
                'samples_data',
            )
        }),
        ('Fechas', {
            'fields': (
                'analysis_date',
                'completion_date'
            )
        }),
        ('Personas Involucradas', {
            'fields': (
                'client',
                'technician'
            )
        }),
        ('Detalles', {
            'fields': (
                'client_requirements',
                'observations',
                'session_comments'
            )
        }),
        ('Estado de Sesión', {
            'fields': (
                'session_status',
            )
        }),
        ('Informe', {
            'fields': (
                'report_files',
            )
        }),
        ('Metadatos', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )


@admin.register(SEMSample)
class SEMSampleAdmin(admin.ModelAdmin):
    list_display = [
        'identification',
        'name',
        'analysis',
        'created_at'
    ]
    list_filter = [
        'analysis__analysis_type',
        'created_at'
    ]
    search_fields = [
        'identification',
        'name',
        'analysis__registration_number'
    ]
