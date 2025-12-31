# accounts/urls.py
from django.urls import path, re_path, include
from . import views
from .views_login import LoginICTS
from .views_password_reset import (
    PasswordResetViewBranded,
    PasswordResetDoneViewBranded,
    PasswordResetConfirmViewBranded,
    PasswordResetCompleteViewBranded,
)

app_name = "accounts"

urlpatterns = [
    # Router y logins
    path("login/", views.login_router, name="login"),
    path("login/icts/", LoginICTS.as_view(), name="login_icts"),
    path("login/dtf/", views.LoginDTF.as_view(), name="login_dtf"),

    # Logout
    path("logout/", views.logout_view, name="logout"),

    # Registro DTF (si lo usas)
    path("register/dtf/", views.register_dtf, name="register_dtf"),

    # Reset de contraseña con branding
    path("password/reset/", PasswordResetViewBranded.as_view(), name="password_reset"),
    path("password/reset/done/", PasswordResetDoneViewBranded.as_view(), name="password_reset_done"),
    re_path(
        r"^password/reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$",
        PasswordResetConfirmViewBranded.as_view(),
        name="password_reset_confirm",
    ),
    path("password/reset/complete/", PasswordResetCompleteViewBranded.as_view(), name="password_reset_complete"),

    # Auth de Django bajo subnamespace para evitar choques
    path("djauth/", include(("django.contrib.auth.urls", "auth"), namespace="djauth")),
]
