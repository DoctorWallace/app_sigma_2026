from functools import wraps
from urllib.parse import quote as urlquote

from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from core.roles import (
    DTF_USER_GROUPS,
    MEC_TECH_GROUPS,
    DP_TECH_GROUPS,
    OPTICS_TECH_GROUPS,
    SLAB_TECH_GROUPS,
    get_normalized_user_groups,
    normalize_group_name,
    user_can_access_dtf,
)
from dtf.models import DTFUserProfile


def dtf_required(view):
    """Require authenticated DTF session and DTF access."""
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('accounts:login_dtf')}?next=" + urlquote(request.get_full_path()))
        if not user_can_access_dtf(request.user):
            return redirect(f"{reverse('accounts:login_dtf')}?next=" + urlquote(request.get_full_path()))
        if request.session.get("module") != "dtf":
            return redirect(f"{reverse('accounts:login_dtf')}?next=" + urlquote(request.get_full_path()))
        return view(request, *args, **kwargs)
    return _wrapped


def dtf_lab_gate(lab_code: str, allow_user_group: bool = True, allow_tech_group: bool = True):
    """Require DTF access and enforce lab-scoped ACL + profile gating."""
    default_user_group = {normalize_group_name("usuarios_dtf")}
    slab_user_groups = {
        normalize_group_name("usuarios_dtf"),
        normalize_group_name("usuarios_autonomo_s_lab"),
    }
    user_groups_by_lab = {
        "s_lab": slab_user_groups,
        "s_mec": default_user_group,
        "s_dp": default_user_group,
        "s_optics": default_user_group,
    }
    tech_groups_by_lab = {
        "s_mec": MEC_TECH_GROUPS,
        "s_lab": SLAB_TECH_GROUPS,
        "s_dp": DP_TECH_GROUPS,
        "s_optics": OPTICS_TECH_GROUPS,
    }
    restriction_field_by_lab = {
        "s_mec": "acceso_s_mec_restringido",
        "s_lab": "acceso_s_lab_restringido",
        "s_dp": "acceso_s_dp_restringido",
        "s_optics": "acceso_s_optics_restringido",
    }

    def decorator(view):
        @wraps(view)
        @dtf_required
        def _wrapped(request, *args, **kwargs):
            user = request.user
            groups = get_normalized_user_groups(user)
            tech_groups = tech_groups_by_lab.get(lab_code, set())
            user_groups = user_groups_by_lab.get(lab_code, default_user_group)

            allowed_groups = set()
            if allow_user_group:
                allowed_groups |= user_groups
            if allow_tech_group:
                allowed_groups |= tech_groups

            if not user.is_superuser and not (groups & allowed_groups):
                raise PermissionDenied

            is_lab_tech = bool(groups & tech_groups)
            if not user.is_superuser and not is_lab_tech:
                profile, _ = DTFUserProfile.objects.get_or_create(user=user)
                if not profile.info_importante_completada:
                    return redirect(reverse("dtf:info-importante"))
                restriction_field = restriction_field_by_lab.get(lab_code)
                if restriction_field and getattr(profile, restriction_field, False):
                    messages.error(request, "Tu acceso a este laboratorio ha sido restringido.")
                    return redirect(reverse("dtf:dashboard"))

            return view(request, *args, **kwargs)

        return _wrapped

    return decorator
