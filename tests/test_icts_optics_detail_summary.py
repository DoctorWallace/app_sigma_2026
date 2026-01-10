import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal


@pytest.mark.django_db
def test_proposal_detail_renders_optics_summary_view(client):
    User = get_user_model()
    user = User.objects.create_user(
        username="optics_detail",
        password="safe-pass",
        email="optics_detail@example.com",
    )
    group, _ = Group.objects.get_or_create(name="icts_users")
    user.groups.add(group)

    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Optics detail",
        facility_optics=True,
        facility_data={
            "optics": {
                "optics_sample_0_identification": "OPT-001",
                "optics_sample_0_name": "Sample A",
                "optics_measurement_mode": "absorption",
                "optics_wavelength_min": "1000",
                "optics_wavelength_min_unit": "nm",
                "optics_wavelength_max": "4000",
                "optics_wavelength_max_unit": "nm",
                "optics_measurement_type": "ftir",
            }
        },
    )

    client.force_login(user)
    response = client.get(reverse("icts:proposal_detail", args=[proposal.pk]))
    assert response.status_code == 200
    html = response.content.decode()
    assert "OPT" in html
    assert "OPT-001" in html
