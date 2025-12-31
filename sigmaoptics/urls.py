from django.urls import path
from . import views

app_name = 'sigmaoptics'

urlpatterns = [
    path('', views.solicitud_list, name='panel_usuario'),
    # Panel técnico
    path('panel/tecnico/', views.panel_tecnico, name='panel_tecnico'),
    
    # Gestión de solicitudes
    path('solicitud/create/', views.solicitud_create, name='solicitud_create'),
    path('solicitud/<int:pk>/', views.solicitud_detail, name='solicitud_detail'),
    path('solicitud/', views.solicitud_list, name='solicitud_list'),
    
    # Acciones del técnico
    path('solicitud/<int:pk>/accept/', views.solicitud_accept, name='solicitud_accept'),
    path('solicitud/<int:pk>/reject/', views.solicitud_reject, name='solicitud_reject'),
    path('solicitud/<int:pk>/start/', views.solicitud_start, name='solicitud_start'),
    path('solicitud/<int:pk>/finish/', views.solicitud_finish, name='solicitud_finish'),
    
    # Gestión de resultados
    path('solicitud/<int:pk>/resultado/', views.resultado_upload, name='resultado_upload'),
    
    # AJAX endpoints
    path('ajax/muestras-form/', views.get_muestras_form, name='get_muestras_form'),
    
    # Análisis de datos
    path('analisis/create/', views.crear_analisis_datos, name='crear_analisis_datos'),
    path('analisis/', views.analisis_list, name='analisis_list'),
    path('analisis/<int:pk>/', views.analisis_detail, name='analisis_detail'),
]
