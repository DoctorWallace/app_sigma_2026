from django.urls import path
from . import views

app_name = "sigmasims"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("records/", views.record_list, name="record_list"),
    path("records/new/", views.record_create, name="record_create"),
    path("records/bulk/", views.record_create_bulk, name="record_create_bulk"),
    path("records/<int:pk>/", views.record_edit, name="record_edit"),
    path("records/<int:pk>/remove/", views.record_remove, name="record_remove"),
    path("records/export.xlsx", views.record_export_xlsx, name="record_export_xlsx"),
    path("docs/", views.docs_list, name="docs_list"),
    path("docs/upload/", views.doc_upload, name="doc_upload"),
    path("docs/<int:pk>/download/", views.doc_download, name="doc_download"),
    path("equipos/", views.equipment_list, name="equipment_list"),
    path("equipos/nuevo/", views.equipment_create, name="equipment_create"),
    path("equipos/<int:equipment_id>/", views.equipment_detail, name="equipment_detail"),
    path("equipos/<int:equipment_id>/editar/", views.equipment_edit, name="equipment_edit"),
    path(
        "equipos/<int:equipment_id>/docrefs/add/",
        views.equipment_docref_add,
        name="equipment_docref_add",
    ),
    path(
        "equipos/docrefs/<int:docref_id>/download/",
        views.equipment_docref_download,
        name="equipment_docref_download",
    ),
    path(
        "equipos/<int:equipment_id>/maintenance/activities/add/",
        views.equipment_maintenance_activity_add,
        name="equipment_maintenance_activity_add",
    ),
    path(
        "equipos/<int:equipment_id>/maintenance/records/add/",
        views.equipment_maintenance_record_add,
        name="equipment_maintenance_record_add",
    ),
    path(
        "equipos/<int:equipment_id>/incidents/add/",
        views.equipment_incident_add,
        name="equipment_incident_add",
    ),
    path(
        "equipos/incidents/<int:incident_id>/download/",
        views.equipment_incident_download,
        name="equipment_incident_download",
    ),
    path("inventario/", views.inventory_list, name="inventory_list"),
    path("inventario/nuevo/", views.inventory_create, name="inventory_create"),
    path("inventario/<int:pk>/editar/", views.inventory_edit, name="inventory_edit"),
    path("plan-anual/", views.annual_plan_view, name="annual_plan"),
    path(
        "plan-anual/copiar/",
        views.annual_plan_copy_previous,
        name="annual_plan_copy_previous",
    ),
    path(
        "plan-anual/historial/",
        views.annual_plan_history,
        name="annual_plan_history",
    ),
    path(
        "plan-anual/entries/nuevo/",
        views.annual_plan_entry_create,
        name="annual_plan_entry_create",
    ),
    path(
        "plan-anual/entries/<int:pk>/editar/",
        views.annual_plan_entry_edit,
        name="annual_plan_entry_edit",
    ),
    path(
        "plan-anual/entries/<int:pk>/borrar/",
        views.annual_plan_entry_delete,
        name="annual_plan_entry_delete",
    ),
    path("proposals/<int:proposal_id>/summary/", views.proposal_summary, name="proposal_summary"),
    path("reports/<int:proposal_id>/", views.report_detail, name="report_detail"),
    path("reports/<int:proposal_id>/edit/", views.report_edit, name="report_edit"),
    path("reports/<int:proposal_id>/add-image/", views.report_add_image, name="report_add_image"),
    path("reports/<int:proposal_id>/add-file/", views.report_add_file, name="report_add_file"),
    path("reports/<int:proposal_id>/export.docx", views.report_export_docx, name="report_export_docx"),
    path("indicators/", views.indicators_dashboard, name="indicators_dashboard"),
    path("materiales-referencia/", views.reference_materials_list, name="reference_materials_list"),
    path("materiales-referencia/nuevo/", views.reference_material_create, name="reference_material_create"),
    path("materiales-referencia/<str:code>/", views.reference_material_detail, name="reference_material_detail"),
    path("materiales-referencia/<str:code>/editar/", views.reference_material_edit, name="reference_material_edit"),
]
