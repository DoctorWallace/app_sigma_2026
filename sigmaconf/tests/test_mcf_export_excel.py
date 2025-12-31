import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from icts.models import AccessProposal
from sigmaconf.models import MCFSession, MCFSampleRecord


def _create_user(username, groups=None):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    for name in groups or []:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


@pytest.mark.django_db
def test_mcf_export_excel_returns_xlsx(client):
    tech = _create_user("mcf_export_tech", ["confocal_technicians"])
    applicant = _create_user("mcf_export_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="MCF Export Proposal",
        facility_confocal=True,
        access_code="ACC-EX",
    )
    session = MCFSession.objects.create(access_proposal=proposal, technician=tech)
    MCFSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        identification="S-1",
        analysis_date=timezone.now().date(),
        roughness=True,
    )
    MCFSampleRecord.objects.create(
        session=session,
        sequence=2,
        source="session",
        identification="S-2",
        analysis_date=timezone.now().date(),
        image_2d=True,
    )

    client.force_login(tech)
    session_data = client.session
    session_data["module"] = "icts"
    session_data.save()

    response = client.get(reverse("sigmaconf:mcf_export_excel", args=[session.pk]))
    assert response.status_code == 200
    assert response["Content-Type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(response.content) > 0
