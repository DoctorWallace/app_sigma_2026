from django.urls import path

from . import views

app_name = "sigmaimp"

urlpatterns = [
    path("dashboard/", views.imp_dashboard, name="imp_dashboard"),
    path("results/", views.imp_results, name="imp_results"),
    path("communications/", views.imp_communications_list, name="imp_communications_list"),
    path(
        "communications/<int:proposal_id>/",
        views.imp_communications_detail,
        name="imp_communications_detail",
    ),
    path("sessions/create/", views.imp_create_session, name="imp_create_session"),
    path(
        "proposals/<int:proposal_id>/sessions/create/",
        views.imp_create_session,
        name="imp_create_session_from_proposal",
    ),
    path("sessions/<int:pk>/", views.imp_session_detail, name="imp_session_detail"),
    path("sessions/<int:pk>/finish/", views.imp_finish_session, name="imp_finish_session"),
    path(
        "sessions/<int:pk>/final-report/upload/",
        views.imp_final_report_upload,
        name="imp_final_report_upload",
    ),
    path("sessions/<int:pk>/notice/", views.imp_notice_download, name="imp_notice_download"),
    path(
        "sessions/<int:pk>/final-report/",
        views.imp_final_report_download,
        name="imp_final_report_download",
    ),
    path(
        "sessions/<int:pk>/registro.xlsx",
        views.imp_export_excel,
        name="imp_export_excel",
    ),
    path("sessions/<int:pk>/samples/add/", views.imp_add_sample, name="imp_add_sample"),
    path("samples/<int:pk>/edit/", views.imp_sample_edit, name="imp_sample_edit"),
]
