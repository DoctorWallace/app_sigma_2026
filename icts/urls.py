from django.urls import path, include
from . import views
from .views_public import ICTSHomeView

app_name = "icts"

urlpatterns = [
    path("", ICTSHomeView.as_view(), name="home"),

    # Dashboard orquestador según rol
    path("dashboard/", views.dashboard, name="dashboard"),
    path("user/", views.icts_user_dashboard, name="user_dashboard"),
    path("implant/dashboard/", views.implant_dashboard, name="implant_dashboard"),

    path("my/", views.my_proposals, name="my_proposals"),
    path("proposal/new/", views.proposal_create, name="proposal_create"),
    path("proposal/<int:pk>/", views.proposal_detail, name="proposal_detail"),
    path("proposal/<int:pk>/edit/", views.proposal_edit, name="proposal_edit"),
    path("proposal/<int:pk>/delete/", views.proposal_delete, name="proposal_delete"),
    path("proposal/<int:pk>/submit/", views.proposal_submit, name="proposal_submit"),
    path("proposal/<int:pk>/decide/", views.proposal_decide, name="proposal_decide"),
    path("proposal-evaluation/", views.proposal_evaluation, name="proposal_evaluation"),
    path("reviews/inbox/", views.reviewer_inbox, name="reviewer_inbox"),
    path("reviews/dashboard/", views.reviewer_dashboard_new, name="reviewer_dashboard_new"),
    path("reviews/history/", views.review_history, name="review_history"),
    path("reviews/mailbox/", views.reviewer_mailbox, name="reviewer_mailbox"),
    path("reviews/faq/", views.reviewer_faq, name="reviewer_faq"),
    path("reviews/start/<int:pk>/", views.review_start, name="review_start"),
    path("responsable/", views.responsable_dashboard, name="responsable_dashboard"),
    path("manager/", views.manager_dashboard, name="manager_dashboard"),
    path("register/", views.RegisterICTSView.as_view(), name="register"),
    path("users/pending/", views.pending_users, name="pending_users"),
    path("users/admin/", views.users_admin, name="users_admin"),
    path("users/approve/<int:user_id>/", views.approve_user, name="approve_user"),
    path("users/reject/<int:user_id>/", views.reject_user, name="reject_user"),
    path("facilities/<slug:slug>/", views.facility_info, name="facility_info"),
    
    # URLs para configuración de técnicas individuales
    path("tech/sem/", views.tech_sem_config, name="tech_sem_config"),
    path("tech/fib/", views.tech_fib_config, name="tech_fib_config"),
    path("tech/imp/", views.tech_imp_config, name="tech_imp_config"),
    path("tech/sims/", views.tech_sims_config, name="tech_sims_config"),
    path("tech/confocal/", views.tech_confocal_config, name="tech_confocal_config"),
    path("tech/olmat/", views.tech_olmat_config, name="tech_olmat_config"),
    path("tech/vdg/", views.tech_vdg_config, name="tech_vdg_config"),
    path("tech/profilometer/", views.tech_profilometer_config, name="tech_profilometer_config"),
    
    # URLs para guardar y cargar borradores de técnicas
    path("save-technique-draft/", views.save_technique_draft, name="save_technique_draft"),
    path("load-technique-draft/", views.load_technique_draft, name="load_technique_draft"),
    path("load-previous-proposal/", views.load_previous_proposal, name="load_previous_proposal"),
    
    # URLs para exportación de datos del manager
    path("manager/export/", views.export_manager_data, name="export_manager_data"),
    path("manager/export-page/", views.manager_export_page, name="manager_export_page"),

    # URLs específicas para OLMAT
    path("olmat/dashboard/", views.olmat_dashboard, name="olmat_dashboard"),
    path("olmat/request/new/<int:proposal_id>/", views.olmat_request_create, name="olmat_request_create"),
    path("olmat/request/<int:request_id>/", views.olmat_request_detail, name="olmat_request_detail"),
    path("olmat/requests/", views.olmat_requests_list, name="olmat_requests_list"),
    path("olmat/request/<int:request_id>/evaluate/", views.olmat_request_evaluate, name="olmat_request_evaluate"),
    
    # SIGMA SEM/FIB
    path("sigmasem/", include("icts.sigmasem.urls")),
    path("sigmasims/", include(("icts.sigmasims.urls", "sigmasims"), namespace="sigmasims")),
]
