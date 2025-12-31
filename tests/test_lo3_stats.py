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


def _set_icts_session(client):
    session = client.session
    session["module"] = "icts"
    session.save()


@pytest.mark.django_db
def test_lo3_stats_calculations(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    technician = _create_user("lo3_tech_stats", ["confocal_technicians"])
    today = timezone.localdate()

    proposal_recent = AccessProposal.objects.create(
        applicant=technician,
        title="P1",
        status="accepted",
        facility_confocal=True,
        submitted_at=timezone.now() - timezone.timedelta(days=20),
    )
    proposal_old = AccessProposal.objects.create(
        applicant=technician,
        title="P2",
        status="accepted",
        facility_confocal=True,
        submitted_at=timezone.now() - timezone.timedelta(days=140),
    )

    session_in_progress_recent = MCFSession.objects.create(
        access_proposal=proposal_recent,
        technician=technician,
    )
    MCFSession.objects.filter(pk=session_in_progress_recent.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=10)
    )

    session_in_progress_old = MCFSession.objects.create(
        access_proposal=proposal_old,
        technician=technician,
    )
    MCFSession.objects.filter(pk=session_in_progress_old.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=120)
    )

    session_completed_recent = MCFSession.objects.create(
        access_proposal=proposal_recent,
        technician=technician,
        status="completed",
        completion_date=today - timezone.timedelta(days=5),
    )
    MCFSession.objects.filter(pk=session_completed_recent.pk).update(
        created_at=timezone.now() - timezone.timedelta(days=25)
    )
    MCFSampleRecord.objects.create(
        session=session_completed_recent,
        sequence=1,
        identification="S-1",
        analysis_date=today - timezone.timedelta(days=3),
        roughness=True,
    )
    session_completed_recent.final_report_pdf.save(
        "final.pdf", ContentFile(b"%PDF-1.4"), save=True
    )

    session_completed_old = MCFSession.objects.create(
        access_proposal=proposal_old,
        technician=technician,
        status="completed",
        completion_date=today - timezone.timedelta(days=120),
    )

    client.force_login(technician)
    _set_icts_session(client)
    response = client.get(reverse("sigmaconf:lo3_home"))
    assert response.status_code == 200
    stats = response.context["stats"]

    assert stats["in_progress_30"] == 1
    assert stats["completed_30"] == 1
    assert stats["in_progress_90"] == 1
    assert stats["completed_90"] == 1
    assert stats["avg_analysis_delay"] == 17.0
    assert stats["completed_total"] == 2
    assert stats["completed_with_report"] == 1
    assert stats["final_report_rate"] == 50.0
