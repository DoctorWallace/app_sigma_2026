import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.template.loader import render_to_string
from django.test import RequestFactory
from types import SimpleNamespace


def _create_user(username: str, group_name: str):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


def _render_base_icts(user):
    rf = RequestFactory()
    request = rf.get("/")
    request.user = user
    request.resolver_match = SimpleNamespace(url_name="dummy")
    return render_to_string("base_icts.html", request=request)


@pytest.mark.django_db
def test_sidebar_hides_profilometer_for_non_dp_technicians():
    """Regression test for the recurring "Perfilometro" leak in sidebars.

    Expected behavior: only DP technicians (or staff/superuser) see the profilometer portal.
    """
    sims_user = _create_user("sims_user_no_prof", "tecnicos_sims")
    html = _render_base_icts(sims_user)
    assert "SIGMA Perfilometro" not in html


@pytest.mark.django_db
def test_sidebar_shows_profilometer_for_dp_technicians():
    dp_user = _create_user("dp_user_prof", "tecnico_responsable_s_dp")
    html = _render_base_icts(dp_user)
    assert "SIGMA Perfilometro" in html
