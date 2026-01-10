import pytest
from datetime import date

from icts.sigmasims.models import SIMSRecord
from icts.sigmasims.services.quality_indicators import compute_i1_stats


def _record_payload(**overrides):
    payload = {
        "reception_date": date(2025, 1, 1),
        "analysis_date": date(2025, 1, 6),
        "sample_identification": "Sample A",
        "client_name": "Client A",
        "sample_characteristics": "Chars",
        "responsible_name": "Resp",
        "client_requirements": "Req",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_compute_i1_stats_handles_pending_and_invalid_records():
    SIMSRecord.objects.create(**_record_payload())
    SIMSRecord.objects.create(
        **_record_payload(
            reception_date=date(2025, 2, 1),
            analysis_date=date(2025, 2, 4),
            sample_identification="Sample B",
        )
    )
    SIMSRecord.objects.create(
        **_record_payload(
            reception_date=date(2025, 3, 1),
            analysis_date=None,
            sample_identification="Sample C",
        )
    )
    invalid = SIMSRecord.objects.create(
        **_record_payload(
            reception_date=date(2025, 4, 1),
            analysis_date=date(2025, 4, 5),
            sample_identification="Sample D",
        )
    )
    SIMSRecord.objects.filter(pk=invalid.pk).update(analysis_date=date(2025, 3, 20))

    stats = compute_i1_stats(SIMSRecord.objects.all())

    assert stats["i1_count"] == 2
    assert stats["i1_avg_days"] == 4.0
    assert stats["i1_median_days"] == 4.0
    assert stats["i1_min_days"] == 3
    assert stats["i1_max_days"] == 5
    assert stats["i1_pending_count"] == 1
    assert stats["i1_invalid_count"] == 1
