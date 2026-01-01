from django.urls import path
from . import views

app_name = "sigmasims"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("records/", views.record_list, name="record_list"),
    path("records/new/", views.record_create, name="record_create"),
    path("records/<int:pk>/", views.record_edit, name="record_edit"),
    path("records/export.xlsx", views.record_export_xlsx, name="record_export_xlsx"),
    path("docs/", views.docs_list, name="docs_list"),
    path("docs/upload/", views.doc_upload, name="doc_upload"),
    path("docs/<int:pk>/download/", views.doc_download, name="doc_download"),
    path("reports/<int:proposal_id>/", views.report_detail, name="report_detail"),
    path("reports/<int:proposal_id>/edit/", views.report_edit, name="report_edit"),
    path("reports/<int:proposal_id>/add-image/", views.report_add_image, name="report_add_image"),
    path("reports/<int:proposal_id>/add-file/", views.report_add_file, name="report_add_file"),
    path("reports/<int:proposal_id>/export.docx", views.report_export_docx, name="report_export_docx"),
    path("indicators/", views.indicators_dashboard, name="indicators_dashboard"),
]
