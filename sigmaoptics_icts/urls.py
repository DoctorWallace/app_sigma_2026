from django.urls import path

from . import views

app_name = "sigmaoptics_icts"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("register/", views.register_view, name="register"),
    path(
        "sessions/from-proposal/<int:proposal_id>/",
        views.create_session_from_proposal,
        name="create_session_from_proposal",
    ),
    path("sessions/<int:pk>/", views.session_detail, name="session_detail"),
    path("sessions/<int:pk>/update/", views.session_update, name="session_update"),
    path("sessions/<int:session_id>/samples/new/", views.sample_add, name="sample_add"),
    path("samples/<int:pk>/edit/", views.sample_edit, name="sample_edit"),
    path("sessions/<int:session_id>/report/", views.report_edit, name="report_edit"),
    path(
        "sessions/<int:session_id>/report/pdf/",
        views.report_pdf_download,
        name="report_pdf_download",
    ),
    path("equipment/", views.equipment_list, name="equipment_list"),
    path("equipment/new/", views.equipment_create, name="equipment_create"),
    path("equipment/<int:equipment_id>/", views.equipment_detail, name="equipment_detail"),
    path("equipment/<int:equipment_id>/edit/", views.equipment_edit, name="equipment_edit"),
    path("equipment/<int:equipment_id>/docs/add/", views.equipment_docref_add, name="equipment_docref_add"),
    path(
        "equipment/<int:equipment_id>/maintenance-activities/add/",
        views.equipment_maintenance_activity_add,
        name="equipment_maintenance_activity_add",
    ),
    path(
        "equipment/<int:equipment_id>/maintenance-records/add/",
        views.equipment_maintenance_record_add,
        name="equipment_maintenance_record_add",
    ),
    path(
        "equipment/<int:equipment_id>/incidents/add/",
        views.equipment_incident_add,
        name="equipment_incident_add",
    ),
    path("equipment/docs/<int:docref_id>/download/", views.equipment_docref_download, name="equipment_docref_download"),
    path(
        "equipment/incidents/<int:incident_id>/download/",
        views.equipment_incident_download,
        name="equipment_incident_download",
    ),
    path("annual-plan/", views.annual_plan_view, name="annual_plan"),
    path("annual-plan/copy/", views.annual_plan_copy_previous, name="annual_plan_copy_previous"),
    path("annual-plan/history/", views.annual_plan_history, name="annual_plan_history"),
    path("annual-plan/entries/new/", views.annual_plan_entry_create, name="annual_plan_entry_create"),
    path("annual-plan/entries/<int:pk>/edit/", views.annual_plan_entry_edit, name="annual_plan_entry_edit"),
    path("annual-plan/entries/<int:pk>/delete/", views.annual_plan_entry_delete, name="annual_plan_entry_delete"),
]
