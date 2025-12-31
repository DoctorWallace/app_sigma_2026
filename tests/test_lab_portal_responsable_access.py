import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse


def _create_user(username, groups=None):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    for name in groups or []:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _set_icts_session(client):
    session = client.session
    session["module"] = "icts"
    session.save()


@pytest.mark.django_db
def test_responsable_cannot_access_lab_portals(client):
    responsable = _create_user("lab_responsable", ["responsables"])
    client.force_login(responsable)
    _set_icts_session(client)

    response = client.get(reverse("sigmaconf:lo3_home"))
    assert response.status_code == 403

    response = client.get(reverse("sigmaconf:mcf_dashboard"))
    assert response.status_code == 403

    response = client.get(reverse("sigmavdg:vdg_home"))
    assert response.status_code == 403

    response = client.get(reverse("sigmaimp:imp_dashboard"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_applicant_can_access_lo3_results(client):
    applicant = _create_user("lo3_results_applicant", ["icts_users"])
    client.force_login(applicant)
    _set_icts_session(client)

    response = client.get(reverse("sigmaconf:lo3_results"))
    assert response.status_code == 200
