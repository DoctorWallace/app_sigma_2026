import pytest
from datetime import date

from icts.sigmasims.models import SIMSRecord


@pytest.mark.django_db
def test_sims_id_generation_increments_by_year():
    record_one = SIMSRecord.objects.create(
        reception_date=date(2025, 2, 1),
        sample_identification="Sample 1",
        client_name="Client 1",
        sample_characteristics="Chars",
        responsible_name="Resp",
        client_requirements="Req",
    )
    record_two = SIMSRecord.objects.create(
        reception_date=date(2025, 3, 1),
        sample_identification="Sample 2",
        client_name="Client 2",
        sample_characteristics="Chars",
        responsible_name="Resp",
        client_requirements="Req",
    )

    assert record_one.sims_id == "SIMS-25-001"
    assert record_two.sims_id == "SIMS-25-002"
