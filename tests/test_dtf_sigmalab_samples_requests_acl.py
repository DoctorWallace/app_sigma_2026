import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from dtf.models import DTFUserProfile
from sigmalab.models import Sample


def _create_user(username, groups):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass")
    for name in groups:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _set_module(client, module="dtf"):
    session = client.session
    session["module"] = module
    session.save()


@pytest.mark.django_db
def test_sigmalab_sample_list_scopes_to_user(client):
    user_a = _create_user("slab_user_a", ["usuarios_dtf"])
    user_b = _create_user("slab_user_b", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user_a,
        info_importante_completada=True,
        acceso_s_lab_restringido=False,
    )
    DTFUserProfile.objects.create(
        user=user_b,
        info_importante_completada=True,
        acceso_s_lab_restringido=False,
    )
    Sample.objects.create(code="25-001", title="A", owner=user_a)
    Sample.objects.create(code="25-002", title="B", owner=user_b)

    client.force_login(user_a)
    _set_module(client)
    response = client.get(reverse("sigmalab:sample-list"))

    assert response.status_code == 200
    samples = response.context["samples"]
    assert samples.count() == 1
    assert samples.first().owner_id == user_a.id


@pytest.mark.django_db
def test_sigmalab_sample_list_allows_slab_tech(client):
    user_a = _create_user("slab_user_a2", ["usuarios_dtf"])
    user_b = _create_user("slab_user_b2", ["usuarios_dtf"])
    tech_slab = _create_user("slab_tech", ["tecnico_responsable_s_lab"])
    DTFUserProfile.objects.create(
        user=user_a,
        info_importante_completada=True,
        acceso_s_lab_restringido=False,
    )
    DTFUserProfile.objects.create(
        user=user_b,
        info_importante_completada=True,
        acceso_s_lab_restringido=False,
    )
    Sample.objects.create(code="25-003", title="A", owner=user_a)
    Sample.objects.create(code="25-004", title="B", owner=user_b)

    client.force_login(tech_slab)
    _set_module(client)
    response = client.get(reverse("sigmalab:sample-list"))

    assert response.status_code == 200
    samples = response.context["samples"]
    assert samples.count() == 2


@pytest.mark.django_db
def test_sigmalab_blocks_other_lab_techs(client):
    tech_mec = _create_user("slab_other_lab", ["tecnico_responsable_s_mec"])

    client.force_login(tech_mec)
    _set_module(client)
    response = client.get(reverse("sigmalab:sample-list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_sigmalab_restriction_blocks_user_endpoints(client):
    user = _create_user("slab_restricted", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user,
        info_importante_completada=True,
        acceso_s_lab_restringido=True,
    )

    client.force_login(user)
    _set_module(client)
    sample_response = client.get(reverse("sigmalab:sample-list"))
    assert sample_response.status_code == 302
    assert sample_response.url == reverse("dtf:dashboard")

    requests_response = client.get(reverse("sigmalab:mis-solicitudes"))
    assert requests_response.status_code == 302
    assert requests_response.url == reverse("dtf:dashboard")


@pytest.mark.django_db
def test_sigmalab_info_importante_required_for_users(client):
    user = _create_user("slab_incomplete", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user,
        info_importante_completada=False,
        acceso_s_lab_restringido=False,
    )

    client.force_login(user)
    _set_module(client)
    response = client.get(reverse("sigmalab:sample-list"))

    assert response.status_code == 302
    assert response.url == reverse("dtf:info-importante")


@pytest.mark.django_db
def test_sigmalab_autonomous_user_group_allowed(client):
    user_auto = _create_user("slab_auto", ["usuarios_autonomo_s_lab"])
    DTFUserProfile.objects.create(
        user=user_auto,
        info_importante_completada=True,
        acceso_s_lab_restringido=False,
    )

    client.force_login(user_auto)
    _set_module(client)
    response = client.get(reverse("sigmalab:sample-list"))

    assert response.status_code == 200
