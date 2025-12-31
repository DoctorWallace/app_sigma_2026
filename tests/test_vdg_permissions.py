import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.urls import reverse

from icts.models import AccessProposal
from sigmavdg.models import VDGSampleRecord, VDGSession


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


def _set_icts_session(client):
    session = client.session
    session["module"] = "icts"
    session.save()


@pytest.mark.django_db
def test_vdg_permissions_edit_and_download(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    applicant = _create_user("vdg_applicant_perm", ["icts_users"])
    technician = _create_user("vdg_tech_perm", ["vdg_technicians"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="VDG Proposal Perm",
        status="accepted",
        facility_vdg=True,
        access_code="ACC-VDG-003",
    )
    session = VDGSession.objects.create(access_proposal=proposal, technician=technician)
    sample = VDGSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        code="S-01",
        material="Steel",
    )
    session.notice_pdf.save("notice.pdf", ContentFile(b"%PDF-1.4\nSIGMA ICTS"), save=True)
    session.report_pdf.save("report.pdf", ContentFile(b"%PDF-1.4\nSIGMA ICTS"), save=True)

    client.force_login(applicant)
    _set_icts_session(client)

    response = client.post(reverse("sigmavdg:vdg_add_sample", args=[session.pk]), data={})
    assert response.status_code == 403

    response = client.get(reverse("sigmavdg:vdg_sample_edit", args=[sample.pk]))
    assert response.status_code == 403

    response = client.post(reverse("sigmavdg:vdg_finish_session", args=[session.pk]))
    assert response.status_code == 403

    response = client.post(reverse("sigmavdg:vdg_session_update", args=[session.pk]), data={})
    assert response.status_code == 403

    response = client.get(reverse("sigmavdg:vdg_notice_download", args=[session.pk]))
    assert response.status_code == 200

    response = client.get(reverse("sigmavdg:vdg_report_download", args=[session.pk]))
    assert response.status_code == 200
