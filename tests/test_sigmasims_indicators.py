import pytest
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal
from icts.sigmasims.models import SIMSRecord, SIMSReport


def _create_user(username, groups):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    for name in groups:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _record_payload(**overrides):
    payload = {
        "reception_date": date(2025, 1, 1),
        "analysis_date": date(2025, 1, 11),
        "sample_identification": "Sample A",
        "client_name": "Client A",
        "sample_characteristics": "Chars",
        "responsible_name": "Resp",
        "client_requirements": "Req",
    }
    payload.update(overrides)
    return payload


def _create_record(**overrides):
    return SIMSRecord.objects.create(**_record_payload(**overrides))


@pytest.mark.django_db
def test_sigmasims_indicators_i1_i2_ok_flags(client):
    tech = _create_user("sims_indicators", ["tecnicos_sims"])
    applicant = _create_user("sims_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="SIMS Indicators",
        facility_sims=True,
    )

    _create_record(access_proposal=proposal)
    SIMSReport.objects.create(
        access_proposal=proposal,
        delivery_date=date(2025, 2, 20),
    )

    client.force_login(tech)
    response = client.get(reverse("icts:sigmasims:indicators_dashboard"), {"year": 2025})

    semester_data = response.context["semester_data"]
    assert semester_data[0]["i1_avg"] == 10.0
    assert semester_data[0]["i1_ok"] is True
    assert semester_data[0]["i2_avg"] == 40.0
    assert semester_data[0]["i2_ok"] is False


@pytest.mark.django_db
def test_sigmasims_indicators_includes_i1_stats(client):
    tech = _create_user("sims_indicators_stats", ["tecnicos_sims"])

    _create_record(
        reception_date=date(2025, 1, 1),
        analysis_date=date(2025, 1, 6),
        sample_identification="Sample A",
    )
    _create_record(
        reception_date=date(2025, 5, 1),
        analysis_date=date(2025, 5, 4),
        sample_identification="Sample B",
    )
    _create_record(
        reception_date=date(2025, 6, 1),
        analysis_date=None,
        sample_identification="Sample C",
    )
    invalid = _create_record(
        reception_date=date(2025, 2, 1),
        analysis_date=date(2025, 2, 10),
        sample_identification="Sample D",
    )
    SIMSRecord.objects.filter(pk=invalid.pk).update(analysis_date=date(2025, 1, 20))

    _create_record(
        reception_date=date(2024, 12, 10),
        analysis_date=date(2024, 12, 12),
        sample_identification="Sample E",
    )
    _create_record(
        reception_date=date(2024, 12, 15),
        analysis_date=None,
        sample_identification="Sample F",
    )

    client.force_login(tech)
    response = client.get(reverse("icts:sigmasims:indicators_dashboard"), {"year": 2025})

    stats = response.context["i1_stats"]
    assert stats["i1_count"] == 2
    assert stats["i1_avg_days"] == 4.0
    assert stats["i1_median_days"] == 4.0
    assert stats["i1_min_days"] == 3
    assert stats["i1_max_days"] == 5
    assert stats["i1_pending_count"] == 1
    assert stats["i1_invalid_count"] == 1
