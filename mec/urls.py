# mec/urls.py
from django.urls import path
from . import views

app_name = "mec"

urlpatterns = [
    path("", views.panel_usuario, name="panel_usuario"),
    path("info-importante/", views.info_importante, name="info_importante"),
    path("panel/tecnico/", views.panel_tecnico_responsable, name="panel_tecnico"),
    path("muestras/nueva/", views.sample_create, name="sample_create"),
    path("solicitudes/nueva/", views.solicitud_create, name="solicitud_create"),
    path("solicitudes/dureza/", views.solicitud_dureza_create, name="solicitud_dureza_create"),
    path("solicitudes/<int:pk>/", views.solicitud_detalle, name="solicitud_detalle"),
    path("solicitudes/<int:pk>/evento/", views.evento_crear, name="evento_crear"),
    path("equipo/", views.ficha_equipo, name="ficha_equipo"),
    path("necesidades/", views.necesidades, name="necesidades"),
    path("inbox/", views.inbox, name="inbox"),
    path("usuarios/crear/", views.crear_usuario, name="crear_usuario"),
    
    # URLs para indicadores de calidad
    path("indicadores/", views.indicadores_calidad, name="indicadores_calidad"),
    path("indicadores/<int:solicitud_id>/actualizar/", views.actualizar_indicador_mec, name="actualizar_indicador_mec"),
]
