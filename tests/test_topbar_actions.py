import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse


def _create_user(username, group_names):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    for name in group_names:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


@pytest.mark.django_db
def test_topbar_points_confocal_to_lo3(client):
    tech = _create_user("lo3_topbar", ["confocal_technicians"])
    client.force_login(tech)
    session = client.session
    session["module"] = "icts"
    session.save()

    response = client.get(reverse("sigmaconf:lo3_home"))
    assert response.status_code == 200
    expected = f'href="{reverse("sigmaconf:lo3_home")}" class="chip"'
    assert expected in response.content.decode()


@pytest.mark.django_db
def test_topbar_points_sem_to_sigmasem(client):
    tech = _create_user("sem_topbar", ["tecnicos_sem_fib"])
    client.force_login(tech)

    response = client.get(reverse("icts:sigmasem:dashboard"))
    assert response.status_code == 200
    expected = f'href="{reverse("icts:sigmasem:dashboard")}" class="chip"'
    assert expected in response.content.decode()


@pytest.mark.django_db
def test_topbar_points_implant_to_portal(client):
    tech = _create_user("imp_topbar", ["implant_technicians"])
    client.force_login(tech)
    session = client.session
    session["module"] = "icts"
    session.save()

    response = client.get(reverse("sigmaimp:imp_dashboard"))
    assert response.status_code == 200
    expected = f'href="{reverse("sigmaimp:imp_dashboard")}" class="chip"'
    assert expected in response.content.decode()
