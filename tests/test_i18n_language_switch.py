import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings
from django.urls import reverse


@pytest.mark.django_db
def test_language_switch_to_english(client):
    User = get_user_model()
    user = User.objects.create_user(
        username="i18n_user",
        password="safe-pass",
        email="i18n_user@example.com",
    )
    group, _ = Group.objects.get_or_create(name="icts_users")
    user.groups.add(group)
    client.force_login(user)

    session = client.session
    session["module"] = "icts"
    session.save()

    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
    response = client.get(reverse("icts:dashboard"), follow=True)
    assert response.status_code == 200
    assert response.wsgi_request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME) == "en"
    assert response.wsgi_request.LANGUAGE_CODE == "en"
    assert "My User Dashboard" in response.content.decode()
