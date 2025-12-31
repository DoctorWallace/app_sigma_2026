import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from dtf.models import DTFUserProfile


def _create_user(username, groups):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass")
    for name in groups:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _set_dtf_session(client):
    session = client.session
    session["module"] = "dtf"
    session.save()


@pytest.mark.django_db
def test_dtf_smoke_routes_render(client):
    user = _create_user("dtf_smoke_user", ["usuarios_dtf"])
    DTFUserProfile.objects.update_or_create(
        user=user, defaults={"info_importante_completada": True}
    )

    client.force_login(user)
    _set_dtf_session(client)

    urls = [
        reverse("dtf:dashboard"),
        reverse("sigmalab:dashboard"),
        reverse("mec:panel_usuario"),
        reverse("sigmadp:panel_usuario"),
        reverse("sigmaoptics:solicitud_list"),
    ]

    for url in urls:
        response = client.get(url, follow=True)
        assert response.status_code == 200
        assert response.templates
