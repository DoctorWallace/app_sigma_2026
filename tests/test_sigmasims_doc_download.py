import pytest
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from icts.sigmasims.models import SIMSDocument


def _create_user(username, groups):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    for name in groups:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


@pytest.mark.django_db
def test_sigmasims_doc_download(client):
    user = _create_user("sims_doc_user", ["tecnicos_sims"])
    document = SIMSDocument.objects.create(
        title="Doc",
        code="DT-TEST",
        version="1",
        date=date(2025, 1, 1),
        file=SimpleUploadedFile("doc.txt", b"dummy"),
        is_active=True,
    )

    client.force_login(user)
    response = client.get(reverse("icts:sigmasims:doc_download", args=[document.pk]))
    assert response.status_code == 200
