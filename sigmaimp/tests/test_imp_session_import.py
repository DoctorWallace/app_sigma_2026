import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal
from sigmaimp.models import IMPSampleRecord, IMPSession


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
def test_imp_create_session_imports_samples(client):
    tech = _create_user("imp_tech", ["implant_technicians"])
    applicant = _create_user("imp_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="IMP Proposal",
        facility_imp=True,
        status="accepted",
        facility_data={
            "imp": {
                "imp_sample_0_identification": "S-1",
                "imp_sample_0_name": "Sample A",
                "imp_sample_0_details": "Details A",
                "imp_sample_1_identification": "S-2",
                "imp_sample_1_name": "Sample B",
                "imp_sample_2_identification": "S-3",
            }
        },
    )

    client.force_login(tech)
    session = client.session
    session["module"] = "icts"
    session.save()

    response = client.post(
        reverse("sigmaimp:imp_create_session_from_proposal", args=[proposal.id])
    )
    assert response.status_code == 302

    session_obj = IMPSession.objects.get(access_proposal=proposal)
    samples = list(session_obj.samples.order_by("sequence"))
    assert len(samples) == 3
    assert samples[0].identification == "S-1"
    assert samples[0].name == "Sample A"
    assert samples[1].identification == "S-2"
    assert samples[2].identification == "S-3"
    assert session_obj.request_snapshot.get("imp_sample_0_identification") == "S-1"


@pytest.mark.django_db
def test_imp_permissions_applicant_view_only(client):
    tech = _create_user("imp_perm_tech", ["implant_technicians"])
    applicant = _create_user("imp_perm_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="IMP Permission",
        facility_imp=True,
        status="accepted",
    )
    session_obj = IMPSession.objects.create(access_proposal=proposal, technician=tech)
    sample = IMPSampleRecord.objects.create(
        session=session_obj,
        sequence=1,
        source="proposal",
        identification="S-1",
    )

    client.force_login(applicant)
    session = client.session
    session["module"] = "icts"
    session.save()

    response = client.get(reverse("sigmaimp:imp_session_detail", args=[session_obj.pk]))
    assert response.status_code == 200

    response = client.get(reverse("sigmaimp:imp_sample_edit", args=[sample.pk]))
    assert response.status_code == 403

    response = client.get(reverse("sigmaimp:imp_add_sample", args=[session_obj.pk]))
    assert response.status_code == 403
