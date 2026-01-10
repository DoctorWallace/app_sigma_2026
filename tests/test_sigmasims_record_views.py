import pytest
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal, ICTSUserProfile
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


@pytest.mark.django_db
def test_sigmasims_record_create_prefills_from_proposal(client):
    tech = _create_user("sims_prefill", ["tecnicos_sims"])
    applicant = _create_user("sims_applicant", ["icts_users"])
    ICTSUserProfile.objects.create(user=applicant, user_siglas="SIMS01")
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="SIMS proposal",
        facility_sims=True,
        status="submitted",
        access_code="SIMS_2025_001",
        facility_data={
            "sims": {
                "sims_sample_0_identification": "SIMS-ID-001",
                "sims_sample_0_details": "Sample details",
            },
        },
    )

    client.force_login(tech)
    response = client.get(
        reverse("icts:sigmasims:record_create"),
        {"proposal_id": proposal.pk},
    )

    assert response.status_code == 200
    form = response.context["form"]
    assert form.initial["request_code"] == "SIMS-2025-001"
    assert form.initial["client_name"] == "sims_applicant"
    assert form.initial["sample_identification"] == "SIMS-ID-001"
    assert form.initial["sample_characteristics"] == "Sample details"
    assert form.fields["access_proposal"].disabled is True
    assert list(form.fields["access_proposal"].queryset) == [proposal]
