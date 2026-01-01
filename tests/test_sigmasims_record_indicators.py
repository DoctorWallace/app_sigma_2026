import pytest
from datetime import date

from icts.sigmasims.models import SIMSRecord


@pytest.mark.django_db
def test_sims_record_i1_days():
    record = SIMSRecord.objects.create(
        reception_date=date(2025, 1, 10),
        analysis_date=date(2025, 1, 15),
        sample_identification="Sample A",
        client_name="Client A",
        sample_characteristics="Chars",
        responsible_name="Resp",
        client_requirements="Req",
    )

    assert record.i1_days == 5
