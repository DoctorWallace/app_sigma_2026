# sigmadp/urls.py
from django.urls import path
from . import views_detect
urlpatterns = [
    path("detectar/", views_detect.detectar_archivo, name="sigmadp_detectar"),
    path("crear/", views_detect.crear_analisis, name="sigmadp_crear"),
]
