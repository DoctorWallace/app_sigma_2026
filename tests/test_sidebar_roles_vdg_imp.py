import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.template.loader import render_to_string
from django.test import RequestFactory
from types import SimpleNamespace


def _create_user(username, group_name):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


def _render_base(user):
    rf = RequestFactory()
    request = rf.get("/")
    request.user = user
    request.resolver_match = SimpleNamespace(url_name="dummy")
    return render_to_string("base_icts.html", request=request)


@pytest.mark.django_db
def test_sidebar_and_role_for_vdg_technician():
    user = _create_user("vdg_user", "vdg_technicians")
    html = _render_base(user)
    assert "Portal L07 (VDG)" in html
    assert "TECNICO VDG" in html


@pytest.mark.django_db
def test_sidebar_and_role_for_imp_technician():
    user = _create_user("imp_user", "imp_technicians")
    html = _render_base(user)
    assert "Ion Implanter" in html
    assert "TECNICO IMP" in html


@pytest.mark.django_db
def test_sidebar_hides_lab_portals_for_responsable():
    user = _create_user("responsable_user", "responsables")
    html = _render_base(user)
    assert "Portal LO3" not in html
    assert "Portal L07 (VDG)" not in html
    assert "Ion Implanter" not in html
