from functools import wraps
from urllib.parse import quote as urlquote

from django.shortcuts import redirect
from django.urls import reverse


def login_required_icts(view_func):
    """Ensure the user is authenticated and logged via the ICTS module."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = f"{reverse('accounts:login_icts')}?next={urlquote(request.get_full_path())}"
            return redirect(login_url)
        if request.session.get("module") != "icts":
            login_url = f"{reverse('accounts:login_icts')}?next={urlquote(request.get_full_path())}"
            return redirect(login_url)
        return view_func(request, *args, **kwargs)

    return _wrapped
