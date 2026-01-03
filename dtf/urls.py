# dtf/urls.py
from django.urls import path, include
from .views_public import DTFHomeView, lab_info
from . import views
from . import views_admin

app_name = "dtf"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("welcome/", DTFHomeView.as_view(), name="welcome"),
    # Información importante
    path("info-importante/", views.info_importante, name="info-importante"),
    path("info-importante/<str:seccion>/", views.info_importante_seccion, name="info-importante-seccion"),
    path("api/marcar-seccion/", views.marcar_seccion_accedida, name="marcar-seccion"),
    # Admin DTF
    path("admin/pending-users/", views_admin.pending_users, name="pending_users"),
    path(
        "admin/pending-users/<int:user_id>/approve/",
        views_admin.approve_user,
        name="approve_user",
    ),
    path(
        "admin/pending-users/<int:user_id>/reject/",
        views_admin.reject_user,
        name="reject_user",
    ),
    # S-LAB bajo /dtf/lab/ con namespace "sigmalab"
    path("lab/", include(("sigmalab.urls", "sigmalab"), namespace="sigmalab")),
    # S-MEC bajo /dtf/mec/ con namespace "mec"
    path("mec/", include(("mec.urls", "mec"), namespace="mec")),
    # Info pública de labs (pre-login)
    path("labs/<slug:slug>/", lab_info, name="lab_info"),
]
