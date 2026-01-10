import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal


ACK_DATA = {
    "ack_empty_scope": "on",
    "ack_empty_previous_experiments": "on",
    "ack_empty_references": "on",
}
REQUIRED_SUBMIT_FIELDS = {
    "project_name": "Project A",
    "project_type": "national",
    "funding_source": "Grant A",
    "start_year": 2024,
    "end_year": 2024,
    "previous_experiments": "Previous experiments",
    "references": "Reference list",
}


def _create_icts_user(username: str, email: str):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass", email=email)
    group, _ = Group.objects.get_or_create(name="icts_users")
    user.groups.add(group)
    return user


def _valid_optics_facility_data():
    return {
        "optics_sample_0_identification": "OPT-001",
        "optics_sample_0_name": "Sample A",
        "optics_sample_0_observations": "Surface OK",
        "optics_recover_samples": False,
        "optics_toxic": False,
        "optics_corrosive": False,
        "optics_irritating": False,
        "optics_radioactive": False,
        "optics_safety_comments": "",
        "optics_measurement_mode": "absorption",
        "optics_wavelength_min": "1000",
        "optics_wavelength_min_unit": "nm",
        "optics_wavelength_max": "4000",
        "optics_wavelength_max_unit": "nm",
        "optics_material": "",
        "optics_measurement_type": "ftir",
        "optics_comments": "",
    }


@pytest.mark.django_db
def test_submit_optics_success_generates_access_code(client):
    user = _create_icts_user("optics_submit_ok", "optics_submit_ok@example.com")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Optics submit",
        facility_optics=True,
        facility_data={"optics": _valid_optics_facility_data()},
        **REQUIRED_SUBMIT_FIELDS,
    )

    client.force_login(user)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]), ACK_DATA)
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "submitted"
    assert proposal.access_code
    assert proposal.access_code.startswith("OPT_")


@pytest.mark.django_db
def test_submit_optics_requires_sample_identification_and_name(client):
    """According to PT-DTF-07, sample Identification AND Name must be present."""
    user = _create_icts_user("optics_submit_sample", "optics_submit_sample@example.com")
    bad = _valid_optics_facility_data()
    bad["optics_sample_0_identification"] = ""
    bad["optics_sample_0_name"] = ""

    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Optics missing sample",
        facility_optics=True,
        facility_data={"optics": bad},
        **REQUIRED_SUBMIT_FIELDS,
    )

    client.force_login(user)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]), ACK_DATA)
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "draft"


@pytest.mark.django_db
def test_submit_optics_rejects_missing_sample_name_even_if_identification_present(client):
    """Quality form PT-DTF-07 has both columns, so Name should be required too."""
    user = _create_icts_user("optics_submit_name", "optics_submit_name@example.com")
    bad = _valid_optics_facility_data()
    bad["optics_sample_0_identification"] = "OPT-001"
    bad["optics_sample_0_name"] = ""  # <-- should trigger validation

    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Optics missing name",
        facility_optics=True,
        facility_data={"optics": bad},
        **REQUIRED_SUBMIT_FIELDS,
    )

    client.force_login(user)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]), ACK_DATA)
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "draft"


@pytest.mark.django_db
def test_submit_optics_requires_measurement_mode(client):
    user = _create_icts_user("optics_submit_mode", "optics_submit_mode@example.com")
    bad = _valid_optics_facility_data()
    bad.pop("optics_measurement_mode", None)

    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Optics missing mode",
        facility_optics=True,
        facility_data={"optics": bad},
        **REQUIRED_SUBMIT_FIELDS,
    )

    client.force_login(user)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]), ACK_DATA)
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "draft"


@pytest.mark.django_db
def test_submit_optics_wavelength_range_and_units_are_validated(client):
    """Min/max must be numeric, have units (nm/um), and min < max after conversion."""
    user = _create_icts_user("optics_submit_wave", "optics_submit_wave@example.com")
    bad = _valid_optics_facility_data()
    bad.update(
        {
            "optics_wavelength_min": "1",
            "optics_wavelength_min_unit": "um",  # 1000 nm
            "optics_wavelength_max": "900",
            "optics_wavelength_max_unit": "nm",  # 900 nm
        }
    )

    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Optics bad wavelength",
        facility_optics=True,
        facility_data={"optics": bad},
        **REQUIRED_SUBMIT_FIELDS,
    )

    client.force_login(user)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]), ACK_DATA)
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "draft"


@pytest.mark.django_db
def test_submit_optics_requires_safety_comments_when_any_hazard_is_checked(client):
    user = _create_icts_user("optics_submit_safety", "optics_submit_safety@example.com")
    bad = _valid_optics_facility_data()
    bad["optics_toxic"] = True
    bad["optics_safety_comments"] = ""

    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Optics toxic without comments",
        facility_optics=True,
        facility_data={"optics": bad},
        **REQUIRED_SUBMIT_FIELDS,
    )

    client.force_login(user)
    response = client.post(reverse("icts:proposal_submit", args=[proposal.pk]), ACK_DATA)
    assert response.status_code == 302

    proposal.refresh_from_db()
    assert proposal.status == "draft"
