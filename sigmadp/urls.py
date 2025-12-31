# sigmadp/urls.py
from django.urls import path
from . import views

app_name = "sigmadp"

urlpatterns = [
    path("", views.panel_usuario, name="panel_usuario"),
    path("panel/tecnico/", views.panel_tecnico_responsable, name="panel_tecnico"),
    path("muestras/nueva/", views.sample_create, name="sample_create"),
    path("solicitudes/nueva/", views.solicitud_create, name="solicitud_create"),
    path("solicitudes/<int:pk>/", views.solicitud_detalle, name="solicitud_detalle"),
    path("solicitudes/<int:pk>/evento/", views.evento_crear, name="evento_crear"),
    path("equipo/", views.ficha_equipo, name="ficha_equipo"),
    path("necesidades/", views.necesidades, name="necesidades"),
    path("inbox/", views.inbox, name="inbox"),
    
    # URLs para solicitudes unificadas
    path("solicitudes/nueva/unificada/", views.solicitud_unificada_create, name="solicitud_unificada_create"),
    path("info-importante/", views.info_importante, name="info_importante"),
    # URLs para solicitudes térmicas (legacy)
    path("termicas/nueva/", views.solicitud_termica_create, name="solicitud_termica_create"),
    path("termicas/<int:pk>/", views.solicitud_termica_detalle, name="solicitud_termica_detalle"),
    path("termicas/bandeja/", views.bandeja_entrada_termica, name="bandeja_entrada_termica"),
    path("termicas/<int:pk>/aceptar/", views.aceptar_solicitud_termica, name="aceptar_solicitud_termica"),
    path("termicas/<int:pk>/rechazar/", views.rechazar_solicitud_termica, name="rechazar_solicitud_termica"),
    path("termicas/<int:pk>/iniciar/", views.iniciar_ensayo_termico, name="iniciar_ensayo_termico"),
    path("termicas/<int:pk>/finalizar/", views.finalizar_ensayo_termico, name="finalizar_ensayo_termico"),
    
    # URLs para análisis de datos
    path("representacion-resultados/", views.representacion_resultados, name="representacion_resultados"),
    path("previsualizar/", views.previsualizar_archivo, name="previsualizar_archivo"),
    path("analisis/crear/", views.crear_analisis_datos, name="crear_analisis_datos"),
    path("analisis/", views.lista_analisis, name="lista_analisis"),
    path("analisis/<int:pk>/", views.detalle_analisis, name="detalle_analisis"),
    
    # URLs para indicadores de calidad
    path("indicadores/", views.indicadores_calidad, name="indicadores_calidad"),
    path("indicadores/<int:solicitud_id>/actualizar/", views.actualizar_indicador, name="actualizar_indicador"),
]



