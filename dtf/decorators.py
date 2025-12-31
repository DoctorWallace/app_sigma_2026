from functools import wraps
from urllib.parse import quote as urlquote

from django.shortcuts import redirect
from django.urls import reverse

from core.roles import user_can_access_dtf


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
