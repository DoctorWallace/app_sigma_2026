# accounts/views.py
from urllib.parse import quote as urlquote

from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from icts.auth_utils import (
    DP_TECH_GROUPS,
    MEC_TECH_GROUPS,
    OPTICS_TECH_GROUPS,
    SLAB_TECH_GROUPS,
    get_normalized_user_groups,
    user_can_access_dtf,
    user_in_groups,
)

from .forms import DTFRegisterForm
from dtf.models import DTFUserProfile


# --- Router de login (elige ICTS o DTF según 'next') ---
def login_router(request):
    nxt = request.GET.get("next") or request.POST.get("next") or ""
    ref = request.META.get("HTTP_REFERER", "") or ""

    # 1) Si hay 'next', decide por prefijo
    if nxt.startswith("/icts/"):
        return redirect(f"{reverse('accounts:login_icts')}?next={urlquote(nxt)}")
    if nxt.startswith("/dtf/") or nxt.startswith("/sigmalab/"):
        return redirect(f"{reverse('accounts:login_dtf')}?next={urlquote(nxt)}")

    # 2) Sin 'next': decide por el referer (desde qué portal venías)
    if "/dtf" in ref or "/sigmalab" in ref:
        return redirect(reverse('accounts:login_dtf'))

    # 3) Por defecto, ICTS
    return redirect(reverse("accounts:login_icts"))


# --- Login DTF ---
class LoginDTF(LoginView):
    template_name = "accounts/login_dtf.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if not user_can_access_dtf(self.request.user):
            logout(self.request)
            messages.error(self.request, "Sin permisos para SIGMA DTF.")
            return redirect("accounts:login_icts")
        self.request.session["module"] = "dtf"
        return response

    def get_success_url(self):
        user = self.request.user
        if not user_can_access_dtf(user):
            messages.error(self.request, "Sin permisos para SIGMA DTF.")
            return reverse("accounts:login_icts")
        next_target = self.request.POST.get("next") or self.request.GET.get("next")
        if next_target and url_has_allowed_host_and_scheme(
            next_target,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return next_target
        groups = get_normalized_user_groups(user)
        # Redireccion automatica segun el rol DTF
        if user_in_groups(user, SLAB_TECH_GROUPS, groups):
            return reverse("sigmalab:panel-tecnico")
        if user_in_groups(user, MEC_TECH_GROUPS, groups):
            return reverse("mec:panel_tecnico")
        if user_in_groups(user, DP_TECH_GROUPS, groups):
            return reverse("sigmadp:panel_tecnico")
        if user_in_groups(user, OPTICS_TECH_GROUPS, groups):
            return reverse("sigmaoptics:panel_tecnico")
        return reverse("dtf:dashboard")


# --- Registro DTF ---
def register_dtf(request):
    if request.method == "POST":
        form = DTFRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data.get("email").lower().strip()
            user.first_name = form.cleaned_data.get("first_name").strip()
            user.last_name = form.cleaned_data.get("last_name").strip()
            user.is_active = False
            user.save()

            # Perfil DTF
            email = user.email
            is_ciemat = True
            DTFUserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "is_ciemat": is_ciemat,
                    "departamento": form.cleaned_data.get("departamento") or "",
                    "division_unidad": form.cleaned_data.get("division_unidad") or "",
                    "matricula": form.cleaned_data.get("username") or "",  # Usar username como matrícula
                    "telefono_interno": form.cleaned_data.get("telefono_interno") or "",
                },
            )

            messages.success(
                request,
                "Registro recibido. Tu cuenta esta pendiente de aprobacion por un tecnico responsable.",
            )
            return redirect("accounts:login_dtf")
        else:
            # Si el formulario no es válido, mostrar errores
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = DTFRegisterForm()
    return render(request, "accounts/register_dtf.html", {"form": form})


# --- Logout común ---
@require_http_methods(["GET", "POST"])
@never_cache
def logout_view(request):
    next_url = request.GET.get("next") or request.POST.get("next")
    module = request.GET.get("module") or request.POST.get("module") or request.session.get("module")
    
    # Limpiar la sesión antes del logout
    request.session.clear()
    logout(request)
    
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    
    # Después del logout, siempre ir al portal principal
    return redirect("/")
