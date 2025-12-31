from django.contrib import admin
from .models import (
    ConfocalSolicitud, ConfocalMuestraIndividual, ConfocalAvance, 
    ConfocalDiarioEntrada, MCFYearCounter, MCFSession, MCFSampleRecord
)


@admin.register(ConfocalSolicitud)
class ConfocalSolicitudAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'solicitante', 'material', 'tipo_microscopia', 
        'numero_muestras', 'estado', 'tecnico_asignado', 'creado_en'
    ]
    list_filter = [
        'estado', 'tipo_microscopia', 'material_radioactivo', 
        'autonomo', 'creado_en', 'tecnico_asignado'
    ]
    search_fields = [
        'material', 'procedencia', 'solicitante__first_name', 
        'solicitante__last_name', 'solicitante__email'
    ]
    readonly_fields = ['creado_en', 'actualizado_en', 'aceptado_en', 'finalizado_en']
    fieldsets = (
        ('Información Básica', {
            'fields': ('solicitante', 'tecnico_asignado', 'becario_asociado', 'estado')
        }),
        ('Detalles de la Solicitud', {
            'fields': ('material', 'numero_muestras', 'tipo_microscopia')
        }),
        ('Parámetros de Confocal', {
            'fields': (
                'longitud_onda_excitacion', 'longitud_onda_emision', 
                'objetivo_requerido', 'espesor_muestra'
            )
        }),
        ('Preparación y Tinción', {
            'fields': ('tincion_utilizada', 'preparacion_muestra')
        }),
        ('Operaciones de Preparación', {
            'fields': (
                'montaje_fluorescente', 'fijacion', 'deshidratacion', 
                'inclusion', 'corte_fino', 'tincion_histologica', 
                'inmunotincion', 'tincion_nuclear'
            ),
            'classes': ('collapse',)
        }),
        ('Información de Seguridad', {
            'fields': ('material_radioactivo', 'manejo_especial', 'tratamiento_previo'),
            'classes': ('collapse',)
        }),
        ('Información Adicional', {
            'fields': ('procedencia', 'otro_dato_importante', 'requisitos_finales', 'observaciones'),
            'classes': ('collapse',)
        }),
        ('Archivos', {
            'fields': ('imagen_muestra', 'croquis'),
            'classes': ('collapse',)
        }),
        ('Tiempo Estimado', {
            'fields': (
                'tiempo_estimado_numero', 'tiempo_estimado_unidad', 
                'tiempo_estimado_indeterminado', 'fecha_estimada_finalizacion'
            ),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('autonomo', 'codigo_muestra', 'creado_en', 'actualizado_en', 'aceptado_en', 'finalizado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ConfocalMuestraIndividual)
class ConfocalMuestraIndividualAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'numero_secuencia', 'identificacion']
    list_filter = ['solicitud__estado', 'solicitud__creado_en']
    search_fields = ['identificacion', 'descripcion', 'solicitud__material']


@admin.register(ConfocalAvance)
class ConfocalAvanceAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'autor', 'tipo', 'creado_en', 'visible_para_usuario']
    list_filter = ['tipo', 'visible_para_usuario', 'creado_en']
    search_fields = ['contenido', 'solicitud__material', 'autor__first_name', 'autor__last_name']
    readonly_fields = ['creado_en']


@admin.register(ConfocalDiarioEntrada)
class ConfocalDiarioEntradaAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'autor', 'fecha', 'etapa']
    list_filter = ['etapa', 'fecha', 'creado_en']
    search_fields = ['nota', 'solicitud__material', 'autor__first_name', 'autor__last_name']
    readonly_fields = ['creado_en']


@admin.register(MCFYearCounter)
class MCFYearCounterAdmin(admin.ModelAdmin):
    list_display = ["year", "counter"]
    ordering = ["-year"]


@admin.register(MCFSession)
class MCFSessionAdmin(admin.ModelAdmin):
    list_display = [
        "lot_code",
        "report_code",
        "access_proposal",
        "technician",
        "status",
        "created_at",
        "completion_date",
    ]
    list_filter = ["status", "created_at", "completion_date"]
    search_fields = ["lot_code", "report_code", "access_proposal__title"]
    readonly_fields = ["lot_code", "report_code", "created_at", "updated_at"]


@admin.register(MCFSampleRecord)
class MCFSampleRecordAdmin(admin.ModelAdmin):
    list_display = [
        "session",
        "sequence",
        "source",
        "identification",
        "operator_name",
        "analysis_date",
    ]
    list_filter = ["source", "analysis_date", "received_date"]
    search_fields = ["identification", "name", "session__lot_code"]
