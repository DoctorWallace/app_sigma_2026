from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dtf.decorators import dtf_admin_required

User = get_user_model()


def _pending_users_qs():
    return (
        User.objects.filter(
            is_active=False,
            dtf_profile__isnull=False,
            is_superuser=False,
        )
        .select_related("dtf_profile")
        .order_by("date_joined")
    )


@dtf_admin_required
def pending_users(request):
    pending = _pending_users_qs()
    return render(
        request,
        "dtf/pending_users.html",
        {
            "pending_users": pending,
            "page_title": "Usuarios DTF pendientes",
        },
    )


@dtf_admin_required
@require_POST
def approve_user(request, user_id):
    user = get_object_or_404(_pending_users_qs(), pk=user_id)
    if not user.dtf_profile.is_ciemat:
        return HttpResponseBadRequest("Invalid DTF profile")

    user.is_active = True
    user.save(update_fields=["is_active"])

    group, _ = Group.objects.get_or_create(name="usuarios_dtf")
    user.groups.add(group)

    return redirect("dtf:pending_users")


@dtf_admin_required
@require_POST
def reject_user(request, user_id):
    user = get_object_or_404(_pending_users_qs(), pk=user_id)
    user.delete()
    return redirect("dtf:pending_users")
