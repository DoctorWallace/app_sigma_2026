import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from icts.models import AccessProposal
from sigmavdg.models import VDGSession


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


def _build_vdg_facility_data():
    return {
        "vdg": {
            "vdg_sample_0_code": "S-100",
            "vdg_sample_0_material": "Al",
            "vdg_sample_0_electron_fluence": "1e15",
            "vdg_sample_0_temperature": "25",
            "vdg_sample_0_atmosphere": "Vacuum",
            "vdg_sample_0_sample_size": "10x10",
            "vdg_sample_0_sample_geometry": "Plate",
        }
    }


@pytest.mark.django_db
def test_vdg_notice_pdf_contains_expected_text(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    applicant = _create_user("vdg_applicant_pdf", ["icts_users"])
    technician = _create_user("vdg_tech_pdf", ["vdg_technicians"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="VDG Proposal PDF",
        status="accepted",
        facility_vdg=True,
        access_code="ACC-VDG-004",
        facility_data=_build_vdg_facility_data(),
    )

    client.force_login(technician)
    _set_icts_session(client)

    response = client.post(
        reverse("sigmavdg:vdg_create_session_from_proposal", args=[proposal.pk])
    )
    assert response.status_code == 302

    session = VDGSession.objects.get(access_proposal=proposal)
    session.received_date = timezone.now().date()
    session.irradiation_start_date = timezone.now().date()
    session.report_issue_date = timezone.now().date()
    session.save(update_fields=["received_date", "irradiation_start_date", "report_issue_date"])

    response = client.post(reverse("sigmavdg:vdg_finish_session", args=[session.pk]))
    assert response.status_code == 302

    session.refresh_from_db()
    assert session.notice_pdf

    with session.notice_pdf.open("rb") as handle:
        content = handle.read()

    assert b"SIGMA ICTS" in content
    assert b"Y:\\" not in content
    assert b"C:\\" not in content
