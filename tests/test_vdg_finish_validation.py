import pytest
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

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
def test_vdg_finish_validation_requires_fields(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    applicant = _create_user("vdg_applicant", ["icts_users"])
    technician = _create_user("vdg_tech", ["vdg_technicians"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="VDG Proposal",
        status="accepted",
        facility_vdg=True,
        access_code="ACC-VDG-001",
    )
    session = VDGSession.objects.create(access_proposal=proposal, technician=technician)
    VDGSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        code="",
        material="",
    )

    client.force_login(technician)
    _set_icts_session(client)

    response = client.post(reverse("sigmavdg:vdg_finish_session", args=[session.pk]))
    assert response.status_code == 302

    session.refresh_from_db()
    assert session.status == "in_progress"
    assert not session.notice_pdf


@pytest.mark.django_db
def test_vdg_finish_validation_date_order(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    applicant = _create_user("vdg_applicant_dates", ["icts_users"])
    technician = _create_user("vdg_tech_dates", ["vdg_technicians"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="VDG Proposal Dates",
        status="accepted",
        facility_vdg=True,
        access_code="ACC-VDG-002",
    )
    session = VDGSession.objects.create(
        access_proposal=proposal,
        technician=technician,
        received_date=timezone.now().date(),
        irradiation_start_date=timezone.now().date() - timedelta(days=1),
        report_issue_date=timezone.now().date() - timedelta(days=2),
    )
    VDGSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        code="S-1",
        material="Steel",
    )

    client.force_login(technician)
    _set_icts_session(client)

    response = client.post(reverse("sigmavdg:vdg_finish_session", args=[session.pk]))
    assert response.status_code == 302

    session.refresh_from_db()
    assert session.status == "in_progress"
    assert not session.notice_pdf
