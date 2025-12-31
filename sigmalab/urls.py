from django.urls import path
from . import views
from . import views_requests as req
from . import views_incidencias as inc

app_name = "sigmalab"

urlpatterns = [
    # Redirecciona según el rol del usuario
    path("", views.dashboard, name="dashboard"),

    # Paneles
    path("panel/usuario/", views.panel_usuario, name="panel-usuario"),
    path("panel/tecnico/", views.panel_tecnico, name="panel-tecnico"),

    # Muestras (demo)
    path("samples/", views.sample_list, name="sample-list"),
    path("samples/new/", views.sample_create, name="sample-create"),

    # Solicitudes (si las traías de labrequest/sigmalab_temp)
    path("requests/new/",  req.nueva_solicitud,   name="nueva-solicitud"),
    path("requests/mine/", req.mis_solicitudes,   name="mis-solicitudes"),
    path("requests/<int:pk>/", req.detalle_solicitud, name="detalle-solicitud"),
    path("requests/<int:pk>/avances/new/", req.nuevo_avance, name="nuevo-avance"),
    path("requests/inbox/", req.bandeja_tecnico,  name="bandeja-tecnico"),
    path("requests/all/",   req.todas_solicitudes, name="todas-solicitudes"),
    path("requests/<int:pk>/estado/", req.cambiar_estado, name="cambiar-estado"),
    
    # Solicitudes de modificación
    path("requests/<int:pk>/modificar/", req.solicitar_modificacion, name="solicitar-modificacion"),
    path("modificaciones/", req.bandeja_modificaciones, name="bandeja-modificaciones"),
    path("modificaciones/<int:pk>/revisar/", req.revisar_modificacion, name="revisar-modificacion"),
    
    # Anulación de solicitudes
    path("requests/<int:pk>/anular/", req.anular_solicitud, name="anular-solicitud"),
    path("requests/<int:pk>/anular-tecnico/", req.anular_solicitud_tecnico, name="anular-solicitud-tecnico"),
    
    # Estimación de tiempo
    path("requests/<int:pk>/aceptar-con-tiempo/", req.aceptar_con_tiempo_estimado, name="aceptar-con-tiempo"),
    
    # Incidencias del laboratorio
    path("incidencias/", inc.reportar_incidencia, name="reportar-incidencia"),
    path("incidencias/mis-incidencias/", inc.mis_incidencias, name="mis-incidencias"),
    path("incidencias/<int:pk>/", inc.detalle_incidencia, name="detalle-incidencia"),
    path("incidencias/inbox/", inc.inbox_incidencias, name="inbox-incidencias"),
    path("incidencias/<int:pk>/gestionar/", inc.gestionar_incidencia, name="gestionar-incidencia"),
    path("incidencias/<int:pk>/responder/", inc.responder_incidencia, name="responder-incidencia"),
    path("incidencias/estadisticas/", inc.estadisticas_incidencias, name="estadisticas-incidencias"),

    # Diario de usuario autónomo
    path("requests/<int:pk>/diario/", views.diario_solicitud, name="diario-solicitud"),
    path("requests/<int:pk>/autonomia/", views.toggle_autonomia, name="toggle-autonomia"),

    # Usuarios (solo técnicos)
    path("usuarios/", views.usuarios_overview, name="usuarios-overview"),
    path("usuarios/crear/", views.crear_usuario, name="crear-usuario"),
    path("usuarios/<int:user_id>/restriccion/<str:modulo>/<str:accion>/", views.gestionar_restriccion, name="restriccion-usuario"),
    path("usuarios/<int:user_id>/detalles/", views.user_details_ajax, name="user-details-ajax"),
    path("equipo/", views.ficha_equipo, name="ficha-equipo"),
    
    # Gestión de becarios
    path("becarios/", views.mis_becarios, name="mis-becarios"),
    path("becarios/gestionar/", views.gestionar_becarios, name="gestionar-becarios"),
    path("becarios/crear/", views.crear_becario, name="crear-becario"),
    path("becarios/<int:becario_id>/", views.detalle_becario, name="detalle-becario"),
    path("becarios/<int:becario_id>/editar/", views.editar_becario, name="editar-becario"),
    path("becarios/<int:becario_id>/estado/<str:nuevo_estado>/", views.cambiar_estado_becario, name="cambiar-estado-becario"),
    path("becarios/<int:becario_id>/eliminar/", views.eliminar_becario, name="eliminar-becario"),
    
    # Gestión de laboratorio
    path("solicitudes/aceptadas/", views.solicitudes_aceptadas, name="solicitudes-aceptadas"),
    path("entrar-laboratorio/", views.entrar_laboratorio, name="entrar-laboratorio"),
    path("entrar-laboratorio/<int:solicitud_id>/", views.entrar_laboratorio, name="entrar-laboratorio-solicitud"),
    
    # Sistema de mensajes internos
    path("mensajes/", views.inbox_mensajes, name="inbox-mensajes"),
    path("mensajes/enviar/", views.enviar_mensaje, name="enviar-mensaje"),
    path("mensajes/<int:mensaje_id>/", views.detalle_mensaje, name="detalle-mensaje"),
    path("mensajes/<int:mensaje_id>/responder/", views.responder_mensaje, name="responder-mensaje"),
    path("mensajes/<int:mensaje_id>/marcar-leido/", views.marcar_mensaje_leido, name="marcar-mensaje-leido"),
    
    # URLs para indicadores de calidad
    path("indicadores/", views.indicadores_calidad, name="indicadores_calidad"),
    path("indicadores/<int:solicitud_id>/actualizar/", views.actualizar_indicador_lab, name="actualizar_indicador_lab"),
    
    # URLs para sistema de equipos
    path("equipos/", views.equipos_lista, name="equipos_lista"),
    path("equipos/crear/", views.equipos_crear, name="equipos_crear"),
    path("equipos/<int:equipo_id>/editar/", views.equipos_editar, name="equipos_editar"),
    path("equipos/<int:equipo_id>/eliminar/", views.equipos_eliminar, name="equipos_eliminar"),
    
    # URLs para préstamos de equipos
    path("prestamos/solicitar/", views.prestamo_solicitar, name="prestamo_solicitar"),
    path("prestamos/mis-prestamos/", views.mis_prestamos, name="mis_prestamos"),
    path("prestamos/<int:prestamo_id>/devolver/", views.prestamo_devolver, name="prestamo_devolver"),
    path("prestamos/gestionar/", views.prestamos_gestionar, name="prestamos_gestionar"),
    path("prestamos/vencidos/", views.prestamos_vencidos, name="prestamos_vencidos"),
    
    # URLs para notificaciones
    path("notificaciones/", views.notificaciones_prestamos, name="notificaciones_prestamos"),
    path("notificaciones/<int:notificacion_id>/marcar-leida/", views.notificacion_marcar_leida, name="notificacion_marcar_leida"),
]
