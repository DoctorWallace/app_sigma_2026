from django.urls import path

from . import views

urlpatterns = [
    path("l07/", views.vdg_home, name="vdg_home"),
    path("l07/dashboard/", views.vdg_dashboard, name="vdg_dashboard"),
    path("l07/equipos/", views.vdg_equipment_list, name="vdg_equipment_list"),
    path("l07/equipos/nuevo/", views.vdg_equipment_create, name="vdg_equipment_create"),
    path(
        "l07/equipos/<int:equipment_id>/",
        views.vdg_equipment_detail,
        name="vdg_equipment_detail",
    ),
    path(
        "l07/equipos/<int:equipment_id>/editar/",
        views.vdg_equipment_edit,
        name="vdg_equipment_edit",
    ),
    path(
        "l07/equipos/<int:equipment_id>/documentos/",
        views.vdg_equipment_document_add,
        name="vdg_equipment_document_add",
    ),
    path(
        "l07/equipos/documentos/<int:document_id>/descargar/",
        views.vdg_equipment_document_download,
        name="vdg_equipment_document_download",
    ),
    path(
        "l07/equipos/<int:equipment_id>/incidencias/",
        views.vdg_equipment_incident_add,
        name="vdg_equipment_incident_add",
    ),
    path(
        "l07/equipos/incidencias/<int:incident_id>/descargar/",
        views.vdg_equipment_incident_download,
        name="vdg_equipment_incident_download",
    ),
    path("l07/items/", views.vdg_item_list, name="vdg_item_list"),
    path("l07/items/nuevo/", views.vdg_item_create, name="vdg_item_create"),
    path("l07/items/movimientos/", views.vdg_item_movements, name="vdg_item_movements"),
    path(
        "l07/items/movimientos/nuevo/",
        views.vdg_item_movement_create,
        name="vdg_item_movement_create",
    ),
    path(
        "l07/items/movimientos/<int:movement_id>/entrada/",
        views.vdg_item_movement_receive,
        name="vdg_item_movement_receive",
    ),
    path("l07/sessions/create/", views.vdg_create_session, name="vdg_create_session"),
    path(
        "l07/sessions/create/<int:proposal_id>/",
        views.vdg_create_session,
        name="vdg_create_session_from_proposal",
    ),
    path("l07/sessions/<int:pk>/", views.vdg_session_detail, name="vdg_session_detail"),
    path("l07/sessions/<int:pk>/update/", views.vdg_session_update, name="vdg_session_update"),
    path("l07/sessions/<int:pk>/add-sample/", views.vdg_add_sample, name="vdg_add_sample"),
    path("l07/sessions/<int:pk>/finish/", views.vdg_finish_session, name="vdg_finish_session"),
    path("l07/sessions/<int:pk>/notice.pdf", views.vdg_notice_download, name="vdg_notice_download"),
    path("l07/sessions/<int:pk>/report.pdf", views.vdg_report_download, name="vdg_report_download"),
    path("l07/samples/<int:pk>/edit/", views.vdg_sample_edit, name="vdg_sample_edit"),
]
