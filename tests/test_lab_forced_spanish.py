import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings
from django.urls import reverse


@pytest.mark.django_db
def test_lab_forced_spanish(client):
    User = get_user_model()
    user = User.objects.create_user(
        username="lo3_lang_user",
        password="safe-pass",
        email="lo3_lang_user@example.com",
    )
    group, _ = Group.objects.get_or_create(name="confocal_technicians")
    user.groups.add(group)
    client.force_login(user)

    session = client.session
    session["module"] = "icts"
    session.save()

    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
    response = client.get(reverse("sigmaconf:lo3_home"))
    assert response.status_code == 200
    assert response.wsgi_request.LANGUAGE_CODE == "es"
