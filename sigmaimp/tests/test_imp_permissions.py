import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from icts.models import AccessProposal
from sigmaimp.models import IMPConversation, IMPMessage, IMPSession, IMPSampleRecord


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
def test_imp_results_view_and_export_permissions(client):
    tech = _create_user("imp_results_tech", ["implant_technicians"])
    applicant = _create_user("imp_results_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="IMP Results",
        facility_imp=True,
        status="accepted",
    )
    session = IMPSession.objects.create(
        access_proposal=proposal,
        technician=tech,
        status="completed",
    )
    IMPSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        identification="S-1",
        implant_date=timezone.now().date(),
    )

    client.force_login(applicant)
    session_data = client.session
    session_data["module"] = "icts"
    session_data.save()

    response = client.get(reverse("sigmaimp:imp_results"))
    assert response.status_code == 200

    response = client.get(reverse("sigmaimp:imp_export_excel", args=[session.pk]))
    assert response.status_code == 200


@pytest.mark.django_db
def test_imp_communications_access(client):
    tech = _create_user("imp_comm_tech", ["implant_technicians"])
    applicant = _create_user("imp_comm_applicant", ["icts_users"])
    other_user = _create_user("imp_comm_other", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="IMP Comms",
        facility_imp=True,
        status="accepted",
    )
    conversation = IMPConversation.objects.create(access_proposal=proposal)
    IMPMessage.objects.create(conversation=conversation, sender=tech, body="Hola")

    client.force_login(applicant)
    session_data = client.session
    session_data["module"] = "icts"
    session_data.save()

    response = client.get(reverse("sigmaimp:imp_communications_list"))
    assert response.status_code == 200

    response = client.get(reverse("sigmaimp:imp_communications_detail", args=[proposal.id]))
    assert response.status_code == 200

    client.force_login(other_user)
    session_data = client.session
    session_data["module"] = "icts"
    session_data.save()

    response = client.get(reverse("sigmaimp:imp_communications_detail", args=[proposal.id]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_imp_finish_session_creates_system_message(client):
    tech = _create_user("imp_finish_tech", ["implant_technicians"])
    applicant = _create_user("imp_finish_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="IMP Finish",
        facility_imp=True,
        status="accepted",
    )
    session = IMPSession.objects.create(
        access_proposal=proposal,
        technician=tech,
        status="in_progress",
    )
    IMPSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        identification="S-1",
        implant_date=timezone.now().date(),
    )

    client.force_login(applicant)
    session_data = client.session
    session_data["module"] = "icts"
    session_data.save()

    response = client.post(reverse("sigmaimp:imp_finish_session", args=[session.pk]))
    assert response.status_code == 403

    client.force_login(tech)
    session_data = client.session
    session_data["module"] = "icts"
    session_data.save()

    response = client.post(reverse("sigmaimp:imp_finish_session", args=[session.pk]))
    assert response.status_code == 302

    session.refresh_from_db()
    assert session.status == "completed"
    assert session.completed_at is not None
    conversation = IMPConversation.objects.get(access_proposal=proposal)
    assert conversation.messages.filter(is_system=True).exists()
