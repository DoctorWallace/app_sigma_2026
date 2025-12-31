from django.contrib import admin
from .models import Sample, Solicitud, Avance

@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "owner", "created_at")
    search_fields = ("code", "title", "owner__username")
    list_filter = ("owner", "created_at")

@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ("id", "solicitante", "estado", "codigo_muestra", "creado_en")
    list_filter = ("estado", "creado_en")
    search_fields = ("id", "codigo_muestra", "solicitante__username")

@admin.register(Avance)
class AvanceAdmin(admin.ModelAdmin):
    list_display = ("id", "solicitud", "autor", "tipo", "visible_para_usuario", "creado_en")
    list_filter = ("tipo", "visible_para_usuario", "creado_en")
    search_fields = ("solicitud__id", "autor__username")
