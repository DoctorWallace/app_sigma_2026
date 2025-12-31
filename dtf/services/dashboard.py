"""
Herramientas para componer el contexto del panel principal DTF.

Centraliza las consultas y agregaciones para mejorar la legibilidad
y facilitar pruebas independientes de la vista.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Sequence

from django.db.models import Count, QuerySet

DEFAULT_STATES: Sequence[str] = (
    "pendiente",
    "aceptada",
    "rechazada",
    "en_curso",
    "finalizada",
)


@dataclass(slots=True)
class LabSummary:
    """Información agregada para un laboratorio concreto."""

    queryset: QuerySet
    counts: Dict[str, int]
    total: int
    latest: list


def _summarize_queryset(
    queryset: QuerySet,
    *,
    state_keys: Sequence[str] = DEFAULT_STATES,
    latest_limit: int = 5,
) -> LabSummary:
    """Devuelve los recuentos y últimas solicitudes de un queryset."""

    counts: Dict[str, int] = {state: 0 for state in state_keys}
    total = 0

    for row in queryset.values("estado").annotate(total=Count("id")):
        state = row["estado"]
        total += row["total"]
        counts[state] = row["total"]

    latest = list(queryset.order_by("-creado_en")[:latest_limit])
    return LabSummary(queryset=queryset, counts=counts, total=total, latest=latest)


def build_dashboard_data(user) -> dict:
    """Devuelve todas las estructuras necesarias para el dashboard DTF."""
    from sigmalab.models import Solicitud
    from mec.models import MecSolicitud
    from sigmadp.models import DpSolicitudTermica
    from sigmaoptics.models import OpticsSolicitud

    querysets = {
        "sigmalab": Solicitud.objects.filter(solicitante=user),
        "mec": MecSolicitud.objects.filter(solicitante=user),
        "sigmadp": DpSolicitudTermica.objects.filter(solicitante=user),
        "sigmaoptics": OpticsSolicitud.objects.filter(solicitante=user),
    }

    labs = {name: _summarize_queryset(qs) for name, qs in querysets.items()}

    totals = {
        "total_solicitudes": sum(summary.total for summary in labs.values()),
        "pendientes": _sum_state(labs.values(), "pendiente"),
        "en_curso": _sum_state(labs.values(), "en_curso"),
        "finalizadas": _sum_state(labs.values(), "finalizada"),
    }

    stats = {
        name: {
            "total": summary.total,
            "pendientes": summary.counts.get("pendiente", 0),
            "aceptadas": summary.counts.get("aceptada", 0),
            "en_curso": summary.counts.get("en_curso", 0),
            "finalizadas": summary.counts.get("finalizada", 0),
            "rechazadas": summary.counts.get("rechazada", 0),
        }
        for name, summary in labs.items()
    }

    return {"labs": labs, "totals": totals, "stats": stats}


def _sum_state(labs: Iterable[LabSummary], state: str) -> int:
    return sum(summary.counts.get(state, 0) for summary in labs)
