from statistics import median
from typing import Iterable

from icts.sigmasims.models import SIMSRecord


def _avg(values):
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def compute_i1_stats(records: Iterable[SIMSRecord]) -> dict:
    only_method = getattr(records, "only", None)
    if callable(only_method):
        records = only_method("reception_date", "analysis_date")

    valid_values = []
    pending_count = 0
    invalid_count = 0

    for record in records:
        reception_date = getattr(record, "reception_date", None)
        analysis_date = getattr(record, "analysis_date", None)
        if not reception_date or not analysis_date:
            if reception_date and not analysis_date:
                pending_count += 1
            continue

        days = (analysis_date - reception_date).days
        if days < 0:
            invalid_count += 1
            continue
        valid_values.append(days)

    return {
        "i1_count": len(valid_values),
        "i1_avg_days": _avg(valid_values),
        "i1_median_days": median(valid_values) if valid_values else None,
        "i1_min_days": min(valid_values) if valid_values else None,
        "i1_max_days": max(valid_values) if valid_values else None,
        "i1_pending_count": pending_count,
        "i1_invalid_count": invalid_count,
    }
