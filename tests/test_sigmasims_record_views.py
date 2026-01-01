import pytest
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.sigmasims.models import SIMSRecord


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
def test_sigmasims_record_list_requires_login(client):
    user = _create_user("sims_list", ["tecnicos_sims"])
    client.force_login(user)
    response = client.get(reverse("icts:sigmasims:record_list"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_sigmasims_record_create(client):
    user = _create_user("sims_create", ["tecnicos_sims"])
    client.force_login(user)
    response = client.post(
        reverse("icts:sigmasims:record_create"),
        {
            "reception_date": date(2025, 1, 5),
            "sample_identification": "Sample A",
            "client_name": "Client A",
            "sample_characteristics": "Chars",
            "responsible_name": "Resp",
            "client_requirements": "Req",
        },
    )
    assert response.status_code == 302
    assert SIMSRecord.objects.count() == 1
