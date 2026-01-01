import pytest
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal
from icts.sigmasims.models import SIMSRecord, SIMSReport


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
def test_sigmasims_indicators_i1_i2_ok_flags(client):
    tech = _create_user("sims_indicators", ["tecnicos_sims"])
    applicant = _create_user("sims_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="SIMS Indicators",
        facility_sims=True,
    )

    SIMSRecord.objects.create(
        access_proposal=proposal,
        reception_date=date(2025, 1, 1),
        analysis_date=date(2025, 1, 11),
        sample_identification="Sample A",
        client_name="Client A",
        sample_characteristics="Chars",
        responsible_name="Resp",
        client_requirements="Req",
    )
    SIMSReport.objects.create(
        access_proposal=proposal,
        delivery_date=date(2025, 2, 20),
    )

    client.force_login(tech)
    response = client.get(reverse("icts:sigmasims:indicators_dashboard"), {"year": 2025})

    semester_data = response.context["semester_data"]
    assert semester_data[0]["i1_avg"] == 10.0
    assert semester_data[0]["i1_ok"] is True
    assert semester_data[0]["i2_avg"] == 40.0
    assert semester_data[0]["i2_ok"] is False
