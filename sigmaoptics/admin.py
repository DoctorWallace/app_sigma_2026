from django.contrib import admin
from .models import OpticsSolicitud, OpticsMuestra, OpticsResultado


@admin.register(OpticsSolicitud)
class OpticsSolicitudAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'material', 'solicitante', 'estado', 
        'medidas_realizar', 'numero_muestras', 'creado_en'
    ]
    list_filter = ['estado', 'medidas_realizar', 'creado_en']
    search_fields = ['material', 'solicitante__username', 'solicitante__first_name', 'solicitante__last_name']
    readonly_fields = ['creado_en', 'aceptado_en', 'finalizado_en']
    ordering = ['-creado_en']


@admin.register(OpticsMuestra)
class OpticsMuestraAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'numero_secuencia', 'identificacion', 'creado_en']
    list_filter = ['creado_en']
    search_fields = ['identificacion', 'descripcion', 'solicitud__material']
    ordering = ['solicitud', 'numero_secuencia']


@admin.register(OpticsResultado)
class OpticsResultadoAdmin(admin.ModelAdmin):
    list_display = ['codigo_informe', 'solicitud', 'creado_por', 'creado_en']
    list_filter = ['creado_en']
    search_fields = ['codigo_informe', 'solicitud__material']
    readonly_fields = ['codigo_informe', 'creado_en']
    ordering = ['-creado_en']