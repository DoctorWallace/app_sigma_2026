import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.urls import reverse


@pytest.mark.django_db
def test_registration_sends_notification_to_responsables(client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.EMAIL_HOST_USER = "no-reply@example.com"
    settings.DEFAULT_FROM_EMAIL = "no-reply@example.com"
    settings.SITE_URL = "http://testserver"

    User = get_user_model()
    responsable = User.objects.create_user(
        username="responsable",
        password="safe-pass",
        email="responsable@example.com",
    )
    group, _ = Group.objects.get_or_create(name="responsables")
    responsable.groups.add(group)

    payload = {
        "username": "newuser",
        "email": "newuser@example.com",
        "first_name": "Nuevo",
        "last_name": "Usuario",
        "password1": "Testpass12345",
        "password2": "Testpass12345",
        "institution": "",
        "phone": "",
        "address": "",
        "matricula": "",
        "accept_terms": "on",
    }

    response = client.post(reverse("icts:register"), payload)
    assert response.status_code == 302

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert "Nuevo usuario" in message.subject
    assert "newuser" in message.body
    assert "newuser@example.com" in message.body
    assert reverse("icts:pending_users") in message.body
