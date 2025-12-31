import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
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
def test_applicant_can_view_but_cannot_edit(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    tech = _create_user("mcf_perm_tech", ["confocal_technicians"])
    applicant = _create_user("mcf_perm_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="MCF Permission Proposal",
        facility_confocal=True,
        access_code="ACC-PERM",
    )
    session = MCFSession.objects.create(
        access_proposal=proposal,
        technician=tech,
        status="completed",
    )
    sample = MCFSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        identification="S-1",
        analysis_date=timezone.now().date(),
        roughness=True,
    )
    session.notice_pdf.save("notice.pdf", ContentFile(b"%PDF-1.4 test"), save=True)

    client.force_login(applicant)
    session_data = client.session
    session_data["module"] = "icts"
    session_data.save()

    response = client.get(reverse("sigmaconf:mcf_sample_edit", args=[sample.pk]))
    assert response.status_code == 403

    response = client.get(reverse("sigmaconf:mcf_notice_download", args=[session.pk]))
    assert response.status_code == 200

    response = client.get(reverse("sigmaconf:mcf_export_excel", args=[session.pk]))
    assert response.status_code == 200
