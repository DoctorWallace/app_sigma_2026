from django.urls import path
from . import views

app_name = 'sigmasem'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard, name='dashboard'),
    
    # Gestión de análisis
    path('create/', views.create_analysis, name='create_analysis'),
    path('analysis/<int:pk>/', views.analysis_detail, name='analysis_detail'),
    path('analysis/', views.analysis_list, name='analysis_list'),
    
    # Gestión de muestras
    path('analysis/<int:analysis_pk>/add-sample/', views.add_sample, name='add_sample'),
    path('analysis/<int:pk>/add-samples/', views.add_samples_to_analysis, name='add_samples_to_analysis'),
    
    # Gestión de sesión
    path('analysis/<int:pk>/update-comments/', views.update_session_comments, name='update_session_comments'),
    path('analysis/<int:pk>/finish-session/', views.finish_session, name='finish_session'),
    
    # Gestión de archivos
    path('browse-files/', views.browse_files, name='browse_files'),
    path('analysis/<int:pk>/update-files/', views.update_report_files, name='update_report_files'),
    path('analysis/<int:pk>/upload-files/', views.upload_files, name='upload_files'),
    path('analysis/<int:pk>/delete-file/', views.delete_file, name='delete_file'),
    path('analysis/<int:pk>/download-file/', views.download_file, name='download_file'),
    path('analysis/<int:pk>/generate-pdf/', views.generate_report_pdf, name='generate_report_pdf'),
    
    # API endpoints
    path('api/proposal/<int:proposal_id>/samples/', views.get_proposal_samples, name='get_proposal_samples'),
]
