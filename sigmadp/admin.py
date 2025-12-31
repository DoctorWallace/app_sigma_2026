from django.contrib import admin
from .models import DpSample, DpSolicitud, DpMuestraNombre, DpEvento, DpNecesidad, DpMensaje


@admin.register(DpSample)
class DpSampleAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'owner', 'creado_en']
    list_filter = ['tipo', 'creado_en']
    search_fields = ['nombre', 'tipo', 'owner__username']
    readonly_fields = ['creado_en']


@admin.register(DpSolicitud)
class DpSolicitudAdmin(admin.ModelAdmin):
    list_display = ['id', 'solicitante', 'material', 'estado', 'creado_en']
    list_filter = ['estado', 'ensayo_desorcion', 'ensayo_permeacion', 'ensayo_difusion', 'ensayo_adsorcion', 'creado_en']
    search_fields = ['solicitante__username', 'material', 'procedencia']
    readonly_fields = ['creado_en', 'actualizado_en']
    
    fieldsets = (
        ('Información General', {
            'fields': ('solicitante', 'tecnico_responsable', 'material', 'procedencia', 'numero_muestras', 'tratamientos', 'estado')
        }),
        ('Ensayo de Desorción', {
            'fields': ('ensayo_desorcion', 'desorcion_temperatura', 'desorcion_tiempo', 'desorcion_presion', 'desorcion_gas', 'desorcion_volumen_muestra'),
            'classes': ('collapse',)
        }),
        ('Ensayo de Permeación', {
            'fields': ('ensayo_permeacion', 'permeacion_temperatura', 'permeacion_presion_alta', 'permeacion_presion_baja', 'permeacion_gas', 'permeacion_espesor_membrana', 'permeacion_area_membrana'),
            'classes': ('collapse',)
        }),
        ('Ensayo de Difusión', {
            'fields': ('ensayo_difusion', 'difusion_temperatura', 'difusion_tiempo', 'difusion_concentracion_inicial', 'difusion_concentracion_final', 'difusion_volumen_solucion'),
            'classes': ('collapse',)
        }),
        ('Ensayo de Adsorción', {
            'fields': ('ensayo_adsorcion', 'adsorcion_temperatura', 'adsorcion_presion', 'adsorcion_gas', 'adsorcion_masa_muestra', 'adsorcion_area_superficie'),
            'classes': ('collapse',)
        }),
        ('Observaciones', {
            'fields': ('observaciones',)
        }),
        ('Fechas', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DpMuestraNombre)
class DpMuestraNombreAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'solicitud']
    search_fields = ['nombre', 'solicitud__id']


@admin.register(DpEvento)
class DpEventoAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'autor', 'creado_en']
    list_filter = ['creado_en']
    search_fields = ['solicitud__id', 'autor__username', 'texto']
    readonly_fields = ['creado_en']


@admin.register(DpNecesidad)
class DpNecesidadAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'fecha', 'creado_por', 'creado_en']
    list_filter = ['fecha', 'creado_en']
    search_fields = ['titulo', 'descripcion', 'creado_por__username']
    readonly_fields = ['creado_en']


@admin.register(DpMensaje)
class DpMensajeAdmin(admin.ModelAdmin):
    list_display = ['asunto', 'autor', 'creado_en']
    list_filter = ['creado_en']
    search_fields = ['asunto', 'mensaje', 'autor__username']
    readonly_fields = ['creado_en']

