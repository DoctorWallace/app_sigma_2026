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


def _login_technician(client, tech_user):
    client.force_login(tech_user)
    session_data = client.session
    session_data["module"] = "icts"
    session_data.save()


@pytest.mark.django_db
def test_mcf_finish_session_requires_identification(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    tech = _create_user("mcf_no_id", ["confocal_technicians"])
    applicant = _create_user("mcf_no_id_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="MCF missing identification",
        facility_confocal=True,
    )
    session = MCFSession.objects.create(access_proposal=proposal, technician=tech)
    MCFSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        identification=" ",
        analysis_date=timezone.now().date(),
        roughness=True,
    )

    _login_technician(client, tech)
    response = client.post(reverse("sigmaconf:mcf_finish_session", args=[session.pk]))
    assert response.status_code == 302

    session.refresh_from_db()
    assert session.status == "in_progress"
    assert not session.notice_pdf


@pytest.mark.django_db
def test_mcf_finish_session_requires_analysis_date(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    tech = _create_user("mcf_no_date", ["confocal_technicians"])
    applicant = _create_user("mcf_no_date_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="MCF missing analysis date",
        facility_confocal=True,
    )
    session = MCFSession.objects.create(access_proposal=proposal, technician=tech)
    MCFSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        identification="S-1",
        roughness=True,
    )

    _login_technician(client, tech)
    response = client.post(reverse("sigmaconf:mcf_finish_session", args=[session.pk]))
    assert response.status_code == 302

    session.refresh_from_db()
    assert session.status == "in_progress"
    assert not session.notice_pdf


@pytest.mark.django_db
def test_mcf_finish_session_requires_measure_flags(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    tech = _create_user("mcf_no_flags", ["confocal_technicians"])
    applicant = _create_user("mcf_no_flags_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="MCF missing flags",
        facility_confocal=True,
    )
    session = MCFSession.objects.create(access_proposal=proposal, technician=tech)
    MCFSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        identification="S-1",
        analysis_date=timezone.now().date(),
    )

    _login_technician(client, tech)
    response = client.post(reverse("sigmaconf:mcf_finish_session", args=[session.pk]))
    assert response.status_code == 302

    session.refresh_from_db()
    assert session.status == "in_progress"
    assert not session.notice_pdf


@pytest.mark.django_db
def test_mcf_finish_session_autofills_received_date(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    tech = _create_user("mcf_auto_received", ["confocal_technicians"])
    applicant = _create_user("mcf_auto_received_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="MCF auto received date",
        facility_confocal=True,
        access_code="ACC-123",
    )
    session = MCFSession.objects.create(access_proposal=proposal, technician=tech)
    analysis_date = timezone.now().date()
    sample = MCFSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        identification="S-1",
        analysis_date=analysis_date,
        roughness=True,
    )

    _login_technician(client, tech)
    response = client.post(reverse("sigmaconf:mcf_finish_session", args=[session.pk]))
    assert response.status_code == 302

    session.refresh_from_db()
    sample.refresh_from_db()
    assert session.status == "completed"
    assert session.notice_pdf
    assert sample.received_date == analysis_date
    assert "[AUTO] received_date asumida = analysis_date" in (sample.observations or "")
