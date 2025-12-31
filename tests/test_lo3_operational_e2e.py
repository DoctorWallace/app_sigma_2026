import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from icts.models import AccessProposal
from sigmaconf.models import MCFSession


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


def _build_confocal_facility_data():
    return {
        "confocal": {
            "confocal_sample_0_identification": "S-001",
            "confocal_sample_0_name": "Sample A",
            "confocal_sample_0_details": "Details A",
            "confocal_sample_1_identification": "S-002",
            "confocal_sample_1_name": "Sample B",
            "confocal_sample_1_details": "Details B",
            "confocal_sample_2_identification": "S-003",
            "confocal_sample_2_name": "Sample C",
            "confocal_sample_2_details": "Details C",
        }
    }


@pytest.mark.django_db
def test_lo3_operational_flow_end_to_end(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    applicant = _create_user("lo3_applicant", ["icts_users"])
    technician = _create_user("lo3_tech", ["confocal_technicians"])

    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="LO3 Accepted Proposal",
        status="accepted",
        facility_confocal=True,
        access_code="ACC-LO3-001",
        facility_data=_build_confocal_facility_data(),
    )

    client.force_login(technician)
    _set_icts_session(client)

    response = client.post(
        reverse("sigmaconf:mcf_create_session_from_proposal", args=[proposal.pk])
    )
    assert response.status_code == 302

    session = MCFSession.objects.get(access_proposal=proposal)
    proposal_samples = list(session.samples.filter(source="proposal").order_by("sequence"))
    assert len(proposal_samples) == 3
    assert proposal_samples[0].identification == "S-001"
    assert proposal_samples[1].identification == "S-002"
    assert proposal_samples[2].identification == "S-003"

    response = client.get(reverse("sigmaconf:mcf_sample_edit", args=[proposal_samples[0].pk]))
    assert response.status_code == 200

    response = client.post(
        reverse("sigmaconf:mcf_add_sample", args=[session.pk]),
        data={
            "identification": "S-EXTRA",
            "analysis_date": timezone.now().date().isoformat(),
            "roughness": "on",
            "indicator_i1": "0",
            "indicator_i2": "0",
        },
    )
    assert response.status_code == 302
    extra_sample = session.samples.get(source="session")
    assert extra_sample.identification == "S-EXTRA"

    analysis_date = timezone.now().date()
    for sample in session.samples.all():
        sample.analysis_date = analysis_date
        sample.roughness = True
        sample.save(update_fields=["analysis_date", "roughness"])

    response = client.post(reverse("sigmaconf:mcf_finish_session", args=[session.pk]))
    assert response.status_code == 302

    session.refresh_from_db()
    assert session.status == "completed"
    assert session.completion_date is not None
    assert session.notice_pdf

    response = client.get(reverse("sigmaconf:mcf_export_excel", args=[session.pk]))
    assert response.status_code == 200
    assert response["Content-Type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    client.force_login(applicant)
    _set_icts_session(client)

    response = client.get(reverse("sigmaconf:mcf_sample_edit", args=[proposal_samples[0].pk]))
    assert response.status_code == 403

    response = client.get(reverse("sigmaconf:mcf_notice_download", args=[session.pk]))
    assert response.status_code == 200

    response = client.get(reverse("sigmaconf:mcf_export_excel", args=[session.pk]))
    assert response.status_code == 200
