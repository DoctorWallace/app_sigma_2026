from django.urls import path

from . import views, views_requests, views_mcf

app_name = "sigmaconf"

urlpatterns = [
    # Main page
    path("", views.confocal_home, name="home"),

    # Legacy requests
    path("solicitud/create/", views_requests.confocal_solicitud_create, name="solicitud_create"),
    path("solicitud/<int:pk>/", views_requests.confocal_solicitud_detail, name="solicitud_detail"),
    path("solicitudes/", views_requests.confocal_solicitud_list, name="solicitud_list"),
    path("solicitud/<int:pk>/accept/", views_requests.confocal_solicitud_accept, name="solicitud_accept"),
    path("solicitud/<int:pk>/reject/", views_requests.confocal_solicitud_reject, name="solicitud_reject"),
    path("solicitud/<int:pk>/start/", views_requests.confocal_solicitud_start, name="solicitud_start"),
    path("solicitud/<int:pk>/finish/", views_requests.confocal_solicitud_finish, name="solicitud_finish"),

    # Dashboard and stats
    path("dashboard/", views_mcf.mcf_dashboard, name="dashboard"),
    path("estadisticas/", views.confocal_estadisticas, name="estadisticas"),

    # LO3 sessions
    path("sessions/create/", views_mcf.mcf_create_session, name="mcf_create_session_legacy"),
    path("sessions/<int:pk>/", views_mcf.mcf_session_detail, name="mcf_session_detail_legacy"),
    path("sessions/<int:pk>/finish/", views_mcf.mcf_finish_session, name="mcf_finish_session_legacy"),
    path("sessions/<int:pk>/add-sample/", views_mcf.mcf_add_sample, name="mcf_add_sample_legacy"),
    path("sessions/<int:pk>/notice.pdf", views_mcf.mcf_notice_download, name="mcf_notice_download_legacy"),
    path("samples/<int:pk>/edit/", views_mcf.mcf_sample_edit, name="mcf_sample_edit_legacy"),

    # LO3 sessions (mcf prefixed)
    path("mcf/", views_mcf.mcf_dashboard, name="mcf_dashboard"),
    path("mcf/create/", views_mcf.mcf_create_session, name="mcf_create_session"),
    path("mcf/create/<int:proposal_id>/", views_mcf.mcf_create_session, name="mcf_create_session_from_proposal"),
    path("mcf/sessions/<int:pk>/", views_mcf.mcf_session_detail, name="mcf_session_detail"),
    path("mcf/sessions/<int:pk>/finish/", views_mcf.mcf_finish_session, name="mcf_finish_session"),
    path("mcf/sessions/<int:pk>/add-sample/", views_mcf.mcf_add_sample, name="mcf_add_sample"),
    path("mcf/sessions/<int:pk>/attachments/", views_mcf.mcf_session_attachment_add, name="mcf_session_attachment_add"),
    path("mcf/sessions/<int:pk>/notice.pdf", views_mcf.mcf_notice_download, name="mcf_notice_download"),
    path("mcf/sessions/<int:pk>/final-report/", views_mcf.mcf_final_report_upload, name="mcf_final_report_upload"),
    path("mcf/sessions/<int:pk>/final-report.pdf", views_mcf.mcf_final_report_download, name="mcf_final_report_download"),
    path("mcf/sessions/<int:pk>/registro.xlsx", views_mcf.mcf_export_excel, name="mcf_export_excel"),
    path("mcf/samples/<int:pk>/edit/", views_mcf.mcf_sample_edit, name="mcf_sample_edit"),
    path("mcf/samples/<int:pk>/attachments/", views_mcf.mcf_sample_attachment_add, name="mcf_sample_attachment_add"),
    path("mcf/attachments/<int:attachment_id>/download/", views_mcf.mcf_attachment_download, name="mcf_attachment_download"),
    path("mcf/attachments/<int:attachment_id>/delete/", views_mcf.mcf_attachment_delete, name="mcf_attachment_delete"),

    # LO3 portal
    path("lo3/", views_mcf.lo3_home, name="lo3_home"),
    path("lo3/resultados/", views_mcf.lo3_results, name="lo3_results"),
    path("lo3/comunicaciones/", views_mcf.lo3_communications_list, name="lo3_communications_list"),
    path(
        "lo3/comunicaciones/<int:proposal_id>/",
        views_mcf.lo3_communications_detail,
        name="lo3_communications_detail",
    ),
    path(
        "lo3/comunicaciones/adjuntos/<int:attachment_id>/",
        views_mcf.lo3_message_attachment_download,
        name="lo3_message_attachment_download",
    ),
    path("lo3/equipos/", views_mcf.lo3_equipment_list, name="lo3_equipment_list"),
    path("lo3/equipos/nuevo/", views_mcf.lo3_equipment_create, name="lo3_equipment_create"),
    path(
        "lo3/equipos/<int:equipment_id>/",
        views_mcf.lo3_equipment_detail,
        name="lo3_equipment_detail",
    ),
    path(
        "lo3/equipos/<int:equipment_id>/editar/",
        views_mcf.lo3_equipment_edit,
        name="lo3_equipment_edit",
    ),
    path(
        "lo3/equipos/<int:equipment_id>/eliminar/",
        views_mcf.lo3_equipment_delete,
        name="lo3_equipment_delete",
    ),
    path(
        "lo3/equipos/<int:equipment_id>/documentos/",
        views_mcf.lo3_equipment_document_add,
        name="lo3_equipment_document_add",
    ),
    path(
        "lo3/equipos/documentos/<int:document_id>/descargar/",
        views_mcf.lo3_equipment_document_download,
        name="lo3_equipment_document_download",
    ),
    path(
        "lo3/equipos/documentos/<int:document_id>/eliminar/",
        views_mcf.lo3_equipment_document_delete,
        name="lo3_equipment_document_delete",
    ),
    path(
        "lo3/calibraciones/<slug:calibration_type>/",
        views_mcf.lo3_calibration_list,
        name="lo3_calibration_list",
    ),
    path(
        "lo3/calibraciones/<slug:calibration_type>/nuevo/",
        views_mcf.lo3_calibration_create,
        name="lo3_calibration_create",
    ),
    path(
        "lo3/calibraciones/<int:calibration_id>/editar/",
        views_mcf.lo3_calibration_edit,
        name="lo3_calibration_edit",
    ),
    path(
        "lo3/calibraciones/<int:calibration_id>/eliminar/",
        views_mcf.lo3_calibration_delete,
        name="lo3_calibration_delete",
    ),
    path(
        "lo3/calibraciones/<int:calibration_id>/certificado/",
        views_mcf.lo3_calibration_certificate_download,
        name="lo3_calibration_certificate_download",
    ),
    path(
        "lo3/materiales/",
        views_mcf.lo3_reference_material_list,
        name="lo3_reference_material_list",
    ),
    path(
        "lo3/materiales/nuevo/",
        views_mcf.lo3_reference_material_create,
        name="lo3_reference_material_create",
    ),
    path(
        "lo3/materiales/<int:material_id>/",
        views_mcf.lo3_reference_material_detail,
        name="lo3_reference_material_detail",
    ),
    path(
        "lo3/materiales/<int:material_id>/editar/",
        views_mcf.lo3_reference_material_edit,
        name="lo3_reference_material_edit",
    ),
    path(
        "lo3/materiales/<int:material_id>/eliminar/",
        views_mcf.lo3_reference_material_delete,
        name="lo3_reference_material_delete",
    ),
    path(
        "lo3/materiales/<int:material_id>/documentos/",
        views_mcf.lo3_reference_material_document_add,
        name="lo3_reference_material_document_add",
    ),
    path(
        "lo3/materiales/documentos/<int:document_id>/descargar/",
        views_mcf.lo3_reference_material_document_download,
        name="lo3_reference_material_document_download",
    ),
    path(
        "lo3/materiales/documentos/<int:document_id>/eliminar/",
        views_mcf.lo3_reference_material_document_delete,
        name="lo3_reference_material_document_delete",
    ),
    path("lo3/incidencias/", views_mcf.lo3_incident_list, name="lo3_incident_list"),
    path(
        "lo3/incidencias/nuevo/",
        views_mcf.lo3_incident_create,
        name="lo3_incident_create",
    ),
    path(
        "lo3/incidencias/<int:incident_id>/",
        views_mcf.lo3_incident_detail,
        name="lo3_incident_detail",
    ),
    path(
        "lo3/incidencias/<int:incident_id>/editar/",
        views_mcf.lo3_incident_edit,
        name="lo3_incident_edit",
    ),
    path(
        "lo3/incidencias/<int:incident_id>/cerrar/",
        views_mcf.lo3_incident_close,
        name="lo3_incident_close",
    ),
    path(
        "lo3/incidencias/<int:incident_id>/adjuntos/",
        views_mcf.lo3_incident_attachment_add,
        name="lo3_incident_attachment_add",
    ),
    path(
        "lo3/incidencias/adjuntos/<int:attachment_id>/descargar/",
        views_mcf.lo3_incident_attachment_download,
        name="lo3_incident_attachment_download",
    ),
    path(
        "lo3/incidencias/adjuntos/<int:attachment_id>/eliminar/",
        views_mcf.lo3_incident_attachment_delete,
        name="lo3_incident_attachment_delete",
    ),
    path(
        "lo3/habilitaciones/",
        views_mcf.lo3_habilitation_list,
        name="lo3_habilitation_list",
    ),
    path(
        "lo3/habilitaciones/nuevo/",
        views_mcf.lo3_habilitation_create,
        name="lo3_habilitation_create",
    ),
    path(
        "lo3/habilitaciones/<int:habilitation_id>/",
        views_mcf.lo3_habilitation_detail,
        name="lo3_habilitation_detail",
    ),
    path(
        "lo3/habilitaciones/<int:habilitation_id>/certificado/",
        views_mcf.lo3_habilitation_download,
        name="lo3_habilitation_download",
    ),
    path(
        "lo3/habilitaciones/<int:habilitation_id>/revocar/",
        views_mcf.lo3_habilitation_revoke,
        name="lo3_habilitation_revoke",
    ),
    path("lo3/<slug:section>/", views_mcf.lo3_section, name="lo3_section"),
]
