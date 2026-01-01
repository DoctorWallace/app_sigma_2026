from django.urls import path
from . import views
app_name = "portal"
urlpatterns = [
    path("", views.home, name="home"),
    path("faq/", views.faq, name="faq"),
    path("icts-access/", views.icts_access, name="icts_access"),
    path(
        "icts-access/solicitud-directa/",
        views.direct_request_create,
        name="direct_request_create",
    ),
    path(
        "icts-access/solicitud-directa/enviado/",
        views.direct_request_success,
        name="direct_request_success",
    ),
]
