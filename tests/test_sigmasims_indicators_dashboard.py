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
def test_sigmasims_indicators_semester_avg(client):
    user = _create_user("sims_indicators", ["tecnicos_sims"])
    SIMSRecord.objects.create(
        reception_date=date(2025, 1, 1),
        analysis_date=date(2025, 1, 11),
        sample_identification="Sample A",
        client_name="Client A",
        sample_characteristics="Chars",
        responsible_name="Resp",
        client_requirements="Req",
    )
    SIMSRecord.objects.create(
        reception_date=date(2025, 2, 1),
        analysis_date=date(2025, 2, 21),
        sample_identification="Sample B",
        client_name="Client B",
        sample_characteristics="Chars",
        responsible_name="Resp",
        client_requirements="Req",
    )

    client.force_login(user)
    response = client.get(reverse("icts:sigmasims:indicators_dashboard"), {"year": 2025})
    assert response.status_code == 200
    semester_data = response.context["semester_data"]
    assert semester_data[0]["i1_avg"] == 15.0
