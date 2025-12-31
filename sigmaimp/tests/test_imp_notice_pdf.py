import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from icts.models import AccessProposal
from sigmaimp.models import IMPSampleRecord, IMPSession
from sigmaimp.views import _build_notice_pdf


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
def test_build_notice_pdf_returns_bytes():
    user = _create_user("imp_notice_user")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="IMP Notice Proposal",
        facility_imp=True,
        access_code="IMP-ACC-001",
    )
    session = IMPSession.objects.create(access_proposal=proposal, technician=user)

    pdf_bytes = _build_notice_pdf(session)
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 1024
    assert session.session_code.encode() in pdf_bytes
    assert proposal.access_code.encode() in pdf_bytes
    assert b"cuenta de usuario SIGMA ICTS" in pdf_bytes
    assert b"Y:\\" not in pdf_bytes
    assert b"C:\\" not in pdf_bytes


@pytest.mark.django_db
def test_imp_finish_session_generates_notice_pdf(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    tech = _create_user("imp_notice_tech", ["implant_technicians"])
    applicant = _create_user("imp_notice_applicant")
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="IMP Finish Proposal",
        facility_imp=True,
        status="accepted",
    )
    session = IMPSession.objects.create(access_proposal=proposal, technician=tech)
    IMPSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        identification="S-1",
        implant_date=timezone.now().date(),
    )

    client.force_login(tech)
    session_data = client.session
    session_data["module"] = "icts"
    session_data.save()

    response = client.post(reverse("sigmaimp:imp_finish_session", args=[session.pk]))
    assert response.status_code == 302

    session.refresh_from_db()
    assert session.status == "completed"
    assert session.notice_pdf
    assert session.notice_pdf.size > 1024
