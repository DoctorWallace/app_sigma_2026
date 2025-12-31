from django.urls import path
from . import views
app_name = "portal"
urlpatterns = [
    path("", views.home, name="home"),
    path("faq/", views.faq, name="faq"),
]
