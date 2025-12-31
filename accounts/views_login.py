# accounts/views_login.py
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from icts.auth_utils import (
    CONF_TECH_GROUPS,
    TECH_SEM_GROUPS,
    get_normalized_user_groups,
    is_manager,
    is_responsable,
    is_reviewer,
    user_can_access_icts,
    user_in_groups,
)

@method_decorator(never_cache, name="dispatch")
class LoginICTS(LoginView):
    template_name = "accounts/login_icts.html"
    redirect_authenticated_user = False  # evita bucles si hay sesión "fantasma"

    def form_valid(self, form):
        response = super().form_valid(form)
        if not user_can_access_icts(self.request.user):
            from django.contrib.auth import logout
            from django.contrib import messages
            logout(self.request)
            messages.error(self.request, "Sin permisos para SIGMA ICTS.")
            return redirect("accounts:login_dtf")
        self.request.session["module"] = "icts"
        return response

    def get_success_url(self):
        user = self.request.user
        if not user_can_access_icts(user):
            return reverse("accounts:login_dtf")
        # respeta ?next=...; si no, redirige según el rol del usuario
        if self.request.GET.get("next"):
            return self.request.GET.get("next")

        # Redirección automática según el rol
        groups = get_normalized_user_groups(user)
        if user_in_groups(user, TECH_SEM_GROUPS, groups):
            return reverse("icts:sigmasem:dashboard")
        if user_in_groups(user, CONF_TECH_GROUPS, groups):
            return reverse("sigmaconf:mcf_dashboard")
        if is_responsable(user, groups):
            return reverse("icts:responsable_dashboard")
        if is_reviewer(user, groups):
            return reverse("icts:reviewer_dashboard_new")
        if is_manager(user, groups):
            return reverse("icts:manager_dashboard")
        return reverse("icts:dashboard")
