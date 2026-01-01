from django.http import HttpResponseForbidden
from django.shortcuts import render

from icts.decorators import login_required_icts
from core import roles as core_roles


def _can_access(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_staff or user.is_superuser:
        return True
    return core_roles.is_any_tech(user)


@login_required_icts
def dashboard(request):
    if not _can_access(request.user):
        return HttpResponseForbidden("No autorizado.")
    return render(request, "sigmaprofilometer/dashboard.html", {})
