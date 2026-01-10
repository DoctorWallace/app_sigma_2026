import pytest
from datetime import date

from icts.sigmasims.models import SIMSRecord


def _record_payload(**overrides):
    payload = {
        "reception_date": date(2025, 1, 10),
        "analysis_date": date(2025, 1, 15),
        "sample_identification": "Sample A",
        "client_name": "Client A",
        "sample_characteristics": "Chars",
        "responsible_name": "Resp",
        "client_requirements": "Req",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_sims_record_i1_days():
    record = SIMSRecord.objects.create(**_record_payload())

    assert record.i1_days == 5


@pytest.mark.django_db
def test_quality_i1_days_returns_int_when_both_dates_present():
    record = SIMSRecord.objects.create(**_record_payload())

    assert record.quality_i1_days == 5


@pytest.mark.django_db
def test_quality_i1_days_returns_none_when_analysis_missing():
    record = SIMSRecord.objects.create(**_record_payload(analysis_date=None))

    assert record.quality_i1_days is None


@pytest.mark.django_db
def test_quality_i1_days_can_be_negative_when_analysis_before_reception():
    record = SIMSRecord(**_record_payload(analysis_date=date(2025, 1, 5)))

    assert record.quality_i1_days == -5
