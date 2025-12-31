# accounts/views_password_reset.py
from django.urls import reverse
from django.utils.http import urlencode
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LoginView

def _brand(req):
    return (req.GET.get("brand") or "").lower()

class PasswordResetViewBranded(auth_views.PasswordResetView):
    """
    /cuentas/password/reset/?brand=icts|dtf
    """
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"

    def get_template_names(self):
        if _brand(self.request) == "icts":
            return ["accounts/password_reset_form_icts.html"]
        return ["accounts/password_reset_form.html"]  # (DTF por defecto)

    def get_success_url(self):
        url = reverse("accounts:password_reset_done")
        b = _brand(self.request)
        return f"{url}?{urlencode({'brand': b})}" if b else url

class PasswordResetDoneViewBranded(auth_views.PasswordResetDoneView):
    def get_template_names(self):
        if _brand(self.request) == "icts":
            return ["accounts/password_reset_done_icts.html"]
        return ["accounts/password_reset_done.html"]

class PasswordResetConfirmViewBranded(auth_views.PasswordResetConfirmView):
    def get_template_names(self):
        if _brand(self.request) == "icts":
            return ["accounts/password_reset_confirm_icts.html"]
        return ["accounts/password_reset_confirm.html"]

    def get_success_url(self):
        url = reverse("accounts:password_reset_complete")
        b = _brand(self.request)
        return f"{url}?{urlencode({'brand': b})}" if b else url

class PasswordResetCompleteViewBranded(auth_views.PasswordResetCompleteView):
    def get_template_names(self):
        if _brand(self.request) == "icts":
            return ["accounts/password_reset_complete_icts.html"]
        return ["accounts/password_reset_complete.html"]



class ICTSLoginView(LoginView):
    template_name = "accounts/login_icts.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.request.GET.get("next") or "/icts/dashboard/"
