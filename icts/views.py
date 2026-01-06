# icts/views.py
from django.contrib import messages
from django.conf import settings
from django.http import Http404, HttpResponseForbidden, HttpResponseBadRequest  # <-- añade esto
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import PermissionDenied
from django.views.generic import FormView
from django.db import transaction, connection
from django.db.models import Count, Q, Avg, F, Max, Case, When, Value, IntegerField
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from datetime import datetime, timedelta
import logging
import json
import re
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from .forms import AccessProposalForm, ParticipantFormSet, AttachmentFormSet, ProposalReviewForm, RegistrationICTSForm, OLMATRequestForm, OLMATEvaluationForm
from django.shortcuts import render
from django.db.models import Exists, OuterRef

from .models import (
    AccessProposal,
    ProposalReview,
    ProposalReviewModificationRequest,
    OLMATRequest,
    ICTSUserProfile,
)
from .utils import (
    build_access_code,
    build_rejected_code,
    build_olmat_access_code,
    ensure_user_siglas,
    get_next_user_sequence,
    send_proposal_notification,
    send_new_user_registration_notification,
    send_user_approval_notification,
)
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test as django_user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME
from functools import wraps
from .auth_utils import (
    CONF_TECH_GROUPS,
    ICTS_CORE_GROUPS,
    OLMAT_TECH_GROUPS,
    TECH_SEM_GROUPS,
    IMP_TECH_GROUPS,
    VDG_TECH_GROUPS,
    get_normalized_user_groups,
    is_icts_user,
    is_manager,
    is_responsable,
    is_reviewer,
    user_in_groups,
)

logger = logging.getLogger(__name__)


def is_plain_icts_user(user):
    """Usuario ICTS sin roles especiales (no revisor, no responsable, no manager)."""
    if not user.is_authenticated or user.is_superuser:
        return False
    group_names = get_normalized_user_groups(user)
    if not group_names & ICTS_CORE_GROUPS:
        return False
    return not (
        is_reviewer(user, group_names)
        or is_responsable(user, group_names)
        or is_manager(user, group_names)
    )


def user_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME, raise_exception=False):
    if not raise_exception:
        return django_user_passes_test(
            test_func, login_url=login_url, redirect_field_name=redirect_field_name
        )

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return _wrapped_view

    return decorator


def _require_reviewer_role(user):
    if not (is_reviewer(user) or is_responsable(user) or is_manager(user)):
        raise PermissionDenied
    return True


def _require_plain_icts_user(user):
    if not is_plain_icts_user(user):
        raise PermissionDenied
    return True


def _build_default_participant_initial(request, proposal=None):
    profile = getattr(request.user, "icts_profile", None)
    if proposal and proposal.applicant_is_different and proposal.contact_person:
        name = proposal.contact_person
    else:
        name = request.user.get_full_name() or request.user.get_username()
    return {
        "name": name,
        "center": (getattr(profile, "center", "") or ""),
        "address": (getattr(profile, "address", "") or ""),
    }


FACILITY_TECH_MAP = {
    "sem": "facility_sem",
    "fib": "facility_sem_fib",
    "imp": "facility_imp",
    "sims": "facility_sims",
    "confocal": "facility_confocal",
    "vdg": "facility_vdg",
    "profilometer": "facility_profilometer",
    "olmat": "facility_olmat",
}


def _filter_facility_data_by_selection(payload, proposal):
    if not isinstance(payload, dict):
        return {}
    filtered = {}
    for key, field in FACILITY_TECH_MAP.items():
        if getattr(proposal, field, False) and key in payload:
            filtered[key] = payload[key]
    return filtered


# --- Technique drafts (session) -------------------------------------------------
# The frontend saves per-technique drafts in the session via /save-technique-draft/.
# When the final proposal POST arrives, facility_data_json may be empty/invalid
# (e.g. due to a JS regression). To make the "sample requests" infallible,
# we rehydrate/merge from session drafts here.
#
# NOTE: These keys are internal and MUST NOT be translated with i18n.
_FACILITY_TECH_MAPPING = {
    "sem": "facility_sem",
    "fib": "facility_sem_fib",
    "imp": "facility_imp",
    "sims": "facility_sims",
    "confocal": "facility_confocal",
    "vdg": "facility_vdg",
    "profilometer": "facility_profilometer",
    "olmat": "facility_olmat",
}


def _get_selected_techniques(proposal):
    return [
        key for key, field in _FACILITY_TECH_MAPPING.items()
        if getattr(proposal, field, False)
    ]


def _get_session_technique_draft_bucket(request, proposal_id):
    """Return {technique_key: draft_dict} for the given proposal_id bucket.

    - New proposal (create): proposal_id is "legacy"
    - Edit: proposal_id is AccessProposal.pk

    Supports older flat session shape: {"sem": {...}, "fib": {...}, ...}
    """
    technique_drafts = request.session.get("technique_drafts", {})
    if not isinstance(technique_drafts, dict):
        return {}

    bucket = technique_drafts.get(str(proposal_id))
    if isinstance(bucket, dict):
        return bucket

    # Compatibility: sometimes drafts were stored flat in session.
    flat = {}
    for tech in _FACILITY_TECH_MAPPING.keys():
        value = technique_drafts.get(tech)
        if isinstance(value, dict):
            flat[tech] = value
    return flat


def _is_blank_value(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _merge_technique_payload(base, draft):
    """Merge two technique dicts, protecting against data loss.

    Rules:
    - For strings/lists/dicts: keep base unless blank, then take draft.
    - For booleans: True wins (base OR draft). This protects against
      frontend defaulting checkboxes to False.
    """
    if not isinstance(base, dict):
        base = {}
    if not isinstance(draft, dict):
        return dict(base)

    merged = dict(base)
    for key, draft_value in draft.items():
        base_value = merged.get(key)

        if isinstance(base_value, bool) and isinstance(draft_value, bool):
            merged[key] = base_value or draft_value
            continue

        if key not in merged or _is_blank_value(base_value):
            merged[key] = draft_value

    return merged


def _apply_session_technique_drafts(request, proposal, payload, proposal_id):
    """Merge session drafts into payload for selected techniques only."""
    if not isinstance(payload, dict):
        payload = {}

    bucket = _get_session_technique_draft_bucket(request, proposal_id)
    if not isinstance(bucket, dict) or not bucket:
        return payload

    for tech in _get_selected_techniques(proposal):
        draft = bucket.get(tech)
        if isinstance(draft, dict) and draft:
            current = payload.get(tech)
            if not isinstance(current, dict):
                current = {}
            payload[tech] = _merge_technique_payload(current, draft)

    return payload


def _selected_facility_techniques(proposal):
    return [tech for tech, field in FACILITY_TECH_MAP.items() if getattr(proposal, field, False)]


def _get_technique_draft_bucket(request, proposal_id):
    technique_drafts = request.session.get("technique_drafts", {})
    if not isinstance(technique_drafts, dict):
        return {}

    bucket = technique_drafts.get(str(proposal_id))
    if isinstance(bucket, dict):
        return bucket

    if any(key in FACILITY_TECH_MAP for key in technique_drafts.keys()):
        return {
            key: value
            for key, value in technique_drafts.items()
            if key in FACILITY_TECH_MAP and isinstance(value, dict)
        }

    return {}


def _fill_facility_data_from_drafts(payload, selected_techniques, request, proposal_id):
    if not isinstance(payload, dict):
        payload = {}
    if not selected_techniques:
        return payload, False

    bucket = _get_technique_draft_bucket(request, proposal_id)
    if not isinstance(bucket, dict) or not bucket:
        return payload, False

    updated = False
    for tech in selected_techniques:
        draft_data = bucket.get(tech)
        if not isinstance(draft_data, dict) or not draft_data:
            continue
        existing = payload.get(tech)
        if not isinstance(existing, dict):
            payload[tech] = draft_data
            updated = True
            continue
        merged = _merge_technique_payload(existing, draft_data)
        if merged != existing:
            payload[tech] = merged
            updated = True

    return payload, updated


IMP_SPECIES_LABELS = {
    "he": "He",
    "ne": "Ne",
    "ar": "Ar",
    "xe": "Xe",
    "h": "H",
    "d": "D",
    "o": "O",
}
IMP_CHAMBER_LABELS = {
    "small_area": "Small area",
    "large_area": "Large area",
}


def _normalize_imp_species(raw_value):
    if isinstance(raw_value, (list, tuple, set)):
        values = [str(item).strip() for item in raw_value if str(item).strip()]
    elif isinstance(raw_value, str):
        values = [raw_value.strip()] if raw_value.strip() else []
    else:
        values = []
    return values


def _parse_facility_data_json(raw_value):
    if raw_value is None:
        return None
    if raw_value == "":
        return {}
    try:
        parsed = json.loads(raw_value)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _validate_imp_data(proposal, facility_data):
    errors = []
    if not getattr(proposal, "facility_imp", False):
        return errors

    payload = {}
    if isinstance(facility_data, dict):
        payload = facility_data.get("imp") or {}
    if not isinstance(payload, dict):
        payload = {}

    species = _normalize_imp_species(payload.get("imp_species"))
    if not species:
        errors.append("Ion Implanter: selecciona al menos una especie.")

    sample_ids = []
    for key, value in payload.items():
        if re.match(r"^imp_sample_\d+_identification$", str(key)):
            if str(value or "").strip():
                sample_ids.append(value)
    if not sample_ids:
        errors.append("Ion Implanter: indica al menos una muestra con identificacion.")

    chamber = (payload.get("imp_chamber") or "").strip()
    if chamber not in {"small_area", "large_area"}:
        errors.append("Ion Implanter: selecciona una camara.")

    def parse_number(key, label, min_value=None, max_value=None, allow_zero=False):
        raw = payload.get(key)
        if raw is None or str(raw).strip() == "":
            errors.append(f"Ion Implanter: {label} es obligatorio.")
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            errors.append(f"Ion Implanter: {label} debe ser un numero.")
            return None
        if not allow_zero and value <= 0:
            errors.append(f"Ion Implanter: {label} debe ser mayor que 0.")
            return None
        if min_value is not None and value < min_value:
            errors.append(f"Ion Implanter: {label} debe ser >= {min_value}.")
        if max_value is not None and value > max_value:
            errors.append(f"Ion Implanter: {label} debe ser <= {max_value}.")
        return value

    energy = parse_number("imp_energy_keV", "energia (keV)", min_value=2, max_value=60, allow_zero=True)
    parse_number("imp_fluence_ion_cm2", "fluencia (ion/cm2)")
    temperature = parse_number("imp_temperature_C", "temperatura (C)", min_value=15, max_value=600, allow_zero=True)
    diameter = parse_number("imp_sample_diameter_mm", "diametro de muestra (mm)")
    parse_number("imp_sample_thickness_mm", "espesor de muestra (mm)")

    if chamber == "large_area" and temperature is not None and temperature > 30:
        errors.append("Ion Implanter: camara large area solo permite temperatura ambiente (<= 30 C).")

    if diameter is not None:
        if chamber == "small_area" and diameter > 10:
            errors.append("Ion Implanter: diametro maximo para small area es 10 mm.")
        if chamber == "large_area" and diameter > 20:
            errors.append("Ion Implanter: diametro maximo para large area es 20 mm.")

    return errors


def _validate_profilometer_data(facility_data):
    errors = []
    if not isinstance(facility_data, dict):
        return errors

    payload = facility_data.get("profilometer") or {}
    if not isinstance(payload, dict):
        payload = {}

    raw_count = payload.get("profilometer_num_samples")
    try:
        count = int(str(raw_count).strip())
    except (TypeError, ValueError):
        errors.append(_("Profilometer: number of samples must be an integer >= 1."))
        return errors

    if count < 1:
        errors.append(_("Profilometer: number of samples must be an integer >= 1."))
        return errors

    for index in range(count):
        sample_id = payload.get(f"profilometer_sample_{index}_id")
        sample_name = payload.get(f"profilometer_sample_{index}_name")
        if not str(sample_id or "").strip() or not str(sample_name or "").strip():
            errors.append(
                _("Profilometer: sample %(index)s requires ID and name.")
                % {"index": index + 1}
            )

    return errors


def _validate_required_steps_for_submit(obj):
    missing = []
    project_type_choices = {choice[0] for choice in AccessProposal.PROJECT_TYPE_CHOICES}

    if _is_blank_value(getattr(obj, "project_name", None)):
        missing.append("Paso 4: Nombre del proyecto")
    project_type = getattr(obj, "project_type", None)
    if _is_blank_value(project_type) or project_type not in project_type_choices:
        missing.append("Paso 4: Tipo de proyecto")
    if _is_blank_value(getattr(obj, "funding_source", None)):
        missing.append("Paso 4: Fuente de financiación")
    start_year = getattr(obj, "start_year", None)
    end_year = getattr(obj, "end_year", None)
    if start_year is None:
        missing.append("Paso 4: Año de inicio")
    if end_year is None:
        missing.append("Paso 4: Año de fin")
    if start_year is not None and end_year is not None and end_year < start_year:
        missing.append("Paso 4: Año fin debe ser >= año inicio")

    if _is_blank_value(getattr(obj, "previous_experiments", None)):
        missing.append("Paso 6: Experimentos previos")
    if _is_blank_value(getattr(obj, "references", None)):
        missing.append("Paso 6: Referencias")

    return missing


def _require_text_or_ack(obj, post):
    def _is_blank_text(value):
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        return False

    missing = []
    if _is_blank_text(getattr(obj, "scope", None)) and not post.get("ack_empty_scope"):
        missing.append("scope")
    if _is_blank_text(getattr(obj, "previous_experiments", None)) and not post.get("ack_empty_previous_experiments"):
        missing.append("previous_experiments")
    if _is_blank_text(getattr(obj, "references", None)) and not post.get("ack_empty_references"):
        missing.append("references")
    return missing


def _count_participants_from_post(request, prefix):
    total_raw = request.POST.get(f"{prefix}-TOTAL_FORMS", "0")
    try:
        total = int(total_raw)
    except (TypeError, ValueError):
        total = 0
    count = 0
    for idx in range(total):
        if request.POST.get(f"{prefix}-{idx}-DELETE") in {"on", "true", "1"}:
            continue
        name = (request.POST.get(f"{prefix}-{idx}-name") or "").strip()
        center = (request.POST.get(f"{prefix}-{idx}-center") or "").strip()
        address = (request.POST.get(f"{prefix}-{idx}-address") or "").strip()
        if name or center or address:
            count += 1
    return max(count, 1)


def _has_icts_facilities(proposal):
    return bool(getattr(proposal, "has_icts_techniques", False))


def _icts_facilities_q(prefix=""):
    query = Q()
    for field in AccessProposal.ICTS_TECH_FIELDS:
        query |= Q(**{f"{prefix}{field}": True})
    return query


def _humanize_label(raw):
    label = str(raw or "").strip()
    if not label:
        return ""
    label_map = {
        "identification": "Identification",
        "name": "Name",
        "details": "Details",
        "sample_type": "Sample type",
        "safety_comments": "Safety comments",
        "analysis_request": "Analysis request",
        "edx_request": "EDX request",
        "selected_elements": "Selected elements",
        "num_samples": "Number of samples",
        "species": "Species",
        "other_species": "Other species / comments",
        "energy_kev": "Energy (keV)",
        "fluence_ion_cm2": "Fluence (ion/cm2)",
        "temperature_c": "Temperature (C)",
        "chamber": "Chamber",
        "sample_diameter_mm": "Sample diameter (mm)",
        "sample_thickness_mm": "Sample thickness (mm)",
        "code": "Code",
        "material": "Material",
        "electron_fluence": "Electron fluence (e-)",
        "temperature": "Temperature (C)",
        "atmosphere": "Atmosphere",
        "sample_size": "Sample size",
        "sample_geometry": "Sample geometry",
        "experiment_description": "Experiment description",
    }
    key = label.lower()
    if key in label_map:
        return label_map[key]
    return label.replace("_", " ").strip().title()


def _format_summary_value(value):
    if isinstance(value, bool):
        return "Si" if value else "No"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value if item not in (None, ""))
    if isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in value.items())
    return value


def _build_facility_data_view(facility_data):
    if not isinstance(facility_data, dict):
        return []

    tech_order = {
        "sem": 1,
        "fib": 2,
        "imp": 3,
        "sims": 4,
        "confocal": 5,
        "vdg": 6,
        "profilometer": 7,
        "olmat": 8,
    }
    tech_labels = {
        "sem": "SEM",
        "fib": "FIB",
        "imp": "IMP",
        "sims": "SIMS",
        "confocal": "CONF",
        "vdg": "VDG",
        "profilometer": "PERF",
        "olmat": "OLMAT",
    }
    pattern = re.compile(r"^(?P<tech>[a-z0-9]+)_sample_(?P<idx>\d+)_(?P<field>.+)$")

    summaries = []
    for tech in sorted(facility_data.keys(), key=lambda t: tech_order.get(t, 999)):
        if tech == "olmat":
            continue
        data = facility_data.get(tech) or {}
        if not isinstance(data, dict):
            continue

        general_fields = []
        samples = {}

        for key, value in data.items():
            if value is None or value == "" or value == {} or value == []:
                continue
            match = pattern.match(key)
            if match:
                idx = int(match.group("idx"))
                field_key = match.group("field")
                label = _humanize_label(field_key)
                samples.setdefault(idx, []).append(
                    {"label": label, "value": _format_summary_value(value)}
                )
            else:
                label_key = key
                prefix = f"{tech}_"
                if label_key.startswith(prefix):
                    label_key = label_key[len(prefix):]
                value_to_show = value
                if tech == "imp" and key == "imp_species":
                    species_values = _normalize_imp_species(value)
                    value_to_show = [
                        IMP_SPECIES_LABELS.get(item.lower(), item) for item in species_values
                    ]
                elif tech == "imp" and key == "imp_chamber":
                    value_to_show = IMP_CHAMBER_LABELS.get(str(value), value)
                general_fields.append(
                    {"label": _humanize_label(label_key), "value": _format_summary_value(value_to_show)}
                )

        if not general_fields and not samples:
            continue

        summaries.append({
            "tech": tech,
            "tech_label": tech_labels.get(tech, str(tech).upper()),
            "general_fields": general_fields,
            "samples": [
                {"index": idx + 1, "fields": samples[idx]}
                for idx in sorted(samples.keys())
            ],
        })

    return summaries


def _ensure_olmat_request_from_submission(proposal, request):
    """Create or update the OLMAT request from facility_data."""
    if not proposal.facility_olmat:
        return None, False

    payload = {}
    if isinstance(proposal.facility_data, dict):
        payload = proposal.facility_data.get("olmat") or {}
    if not isinstance(payload, dict):
        payload = {}

    missing = object()

    def get_value(key):
        if key not in payload:
            return missing
        return payload.get(key)

    def normalize_text(value):
        if value is missing:
            return missing
        if value is None:
            return ""
        return str(value).strip()

    def normalize_list(value):
        if value is missing:
            return missing
        if isinstance(value, bool):
            return missing
        if isinstance(value, (list, tuple, set)):
            return [item for item in value if item not in (None, "")]
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        return []

    def resolve_choice(value, choices, fallback):
        return value if value in choices else fallback

    def build_additional(fallback):
        raw_additional = normalize_text(get_value("olmat_additional_requirements"))
        raw_notes = normalize_text(get_value("olmat_sample_prep_notes"))
        if raw_additional is missing and raw_notes is missing:
            return fallback
        additional = "" if raw_additional is missing else raw_additional
        notes = "" if raw_notes is missing else raw_notes
        if notes:
            tag = f"Prep (otros): {notes}"
            if additional:
                if tag not in additional:
                    additional = f"{additional}\n{tag}"
            else:
                additional = tag
        return additional

    service_choices = {choice[0] for choice in OLMATRequest.SERVICE_TYPE_CHOICES}
    flex_choices = {choice[0] for choice in OLMATRequest._meta.get_field("flexibility").choices}
    default_flex = OLMATRequest._meta.get_field("flexibility").default

    service_raw = get_value("olmat_service_type")
    flexibility_raw = get_value("olmat_flexibility")
    service_type = missing
    flexibility = missing
    if service_raw is not missing:
        service_type = resolve_choice(service_raw, service_choices, "technical")
    if flexibility_raw is not missing:
        flexibility = resolve_choice(flexibility_raw, flex_choices, default_flex)

    defaults = {
        "proponent_name": proposal.contact_person or proposal.applicant.get_full_name() or proposal.applicant.username,
        "proponent_affiliation": proposal.organization or getattr(getattr(proposal.applicant, "icts_profile", None), "center", ""),
        "entity_type": "",
        "activity_description": normalize_text(get_value("olmat_activity_description")),
        "service_type": service_type,
        "irradiation_requirements": normalize_text(get_value("olmat_irradiation_requirements")),
        "diagnostics_needed": normalize_list(get_value("olmat_diagnostics")),
        "sample_preparation": normalize_list(get_value("olmat_sample_prep")),
        "beam_usage": normalize_list(get_value("olmat_beam_usage")),
        "preferred_dates": normalize_text(get_value("olmat_preferred_dates")),
        "flexibility": flexibility,
        "additional_requirements": build_additional(""),
        "status": "pending",
    }

    update_candidates = dict(defaults)

    if defaults["activity_description"] is missing:
        defaults["activity_description"] = (proposal.scope or "").strip()
    if defaults["service_type"] is missing:
        defaults["service_type"] = "technical"
    if defaults["irradiation_requirements"] is missing:
        defaults["irradiation_requirements"] = ""
    if defaults["diagnostics_needed"] is missing:
        defaults["diagnostics_needed"] = []
    if defaults["sample_preparation"] is missing:
        defaults["sample_preparation"] = []
    if defaults["beam_usage"] is missing:
        defaults["beam_usage"] = []
    if defaults["preferred_dates"] is missing:
        defaults["preferred_dates"] = ""
    if defaults["flexibility"] is missing:
        defaults["flexibility"] = default_flex

    olmat_request, created = OLMATRequest.objects.get_or_create(
        proposal=proposal,
        defaults=defaults,
    )

    update_fields = []
    if not created:
        # Only refresh data while the request is pending.
        if olmat_request.status in ("pending", "under_review"):
            updates = {}
            for field, value in update_candidates.items():
                if field == "status":
                    continue
                if value is missing:
                    continue
                updates[field] = value
            updates["additional_requirements"] = build_additional(missing)

            for field, value in updates.items():
                if value is missing:
                    continue
                if getattr(olmat_request, field) != value:
                    setattr(olmat_request, field, value)
                    update_fields.append(field)

    if not olmat_request.access_code:
        olmat_request.access_code = build_olmat_access_code(proposal, olmat_request)
        update_fields.append("access_code")

    if update_fields:
        olmat_request.save(update_fields=update_fields)

    return olmat_request, created


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
@never_cache
def dashboard(request):
    groups = get_normalized_user_groups(request.user)
    if is_manager(request.user, groups):
        return redirect("icts:manager_dashboard")
    if is_responsable(request.user, groups):
        return redirect("icts:responsable_dashboard")
    if is_reviewer(request.user, groups):
        return redirect("icts:reviewer_dashboard_new")
    if user_in_groups(request.user, OLMAT_TECH_GROUPS, groups):
        return redirect("icts:olmat_dashboard")
    if user_in_groups(request.user, IMP_TECH_GROUPS, groups):
        return redirect("sigmaimp:imp_dashboard")
    if user_in_groups(request.user, VDG_TECH_GROUPS, groups):
        return redirect("sigmavdg:vdg_home")
    if user_in_groups(request.user, TECH_SEM_GROUPS, groups):
        return redirect("icts:sigmasem:dashboard")
    if user_in_groups(request.user, CONF_TECH_GROUPS, groups):
        return redirect("sigmaconf:mcf_dashboard")
    return redirect("icts:user_dashboard")


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_plain_icts_user, raise_exception=True)
@never_cache
def icts_user_dashboard(request):
    """
    Panel del usuario: agrupa sus propuestas por estado.
    Filtra por applicant (no owner).
    """
    qs = (
        AccessProposal.objects
        .filter(applicant=request.user)      # <- aquí está la clave
        .order_by("-created_at", "-id")
    )

    reviewed_qs = ProposalReview.objects.filter(
        proposal=OuterRef("pk"),
        status="submitted",
    )
    evaluated = qs.annotate(has_review=Exists(reviewed_qs)).filter(has_review=True)

    drafts = qs.filter(status="draft")
    changes_requested = qs.filter(status="changes_requested")
    evaluated = evaluated.exclude(status="changes_requested")
    submitted = (
        qs.exclude(pk__in=evaluated.values("pk"))
        .exclude(pk__in=drafts.values("pk"))
        .exclude(pk__in=changes_requested.values("pk"))
    )

    # Obtener análisis SEM/FIB asociados a las propuestas del usuario
    from icts.sigmasem.models import SEMAnalysis
    user_analyses = SEMAnalysis.objects.filter(
        access_proposal__applicant=request.user
    ).select_related('access_proposal', 'technician').order_by('-analysis_date')

    from sigmaconf.models import MCFSession
    user_mcf_sessions = MCFSession.objects.filter(
        access_proposal__applicant=request.user,
        status="completed",
    ).select_related("access_proposal", "technician").order_by("-created_at")

    from sigmaimp.models import IMPSession
    user_imp_sessions = IMPSession.objects.filter(
        access_proposal__applicant=request.user,
        status="completed",
    ).select_related("access_proposal", "technician").order_by("-created_at")

    from sigmavdg.models import VDGSession
    user_vdg_sessions = VDGSession.objects.filter(
        access_proposal__applicant=request.user,
        status="completed",
    ).select_related("access_proposal", "technician").order_by("-created_at")

    # Datos para el gráfico de barras (últimos 12 meses)
    from datetime import datetime, timedelta
    proposal_filter = _icts_facilities_q(prefix="proposal__")
    proposal_filter = _icts_facilities_q(prefix="proposal__")
    from django.db.models import Count
    from django.utils import timezone
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=365)
    
    # Solicitudes enviadas por mes
    submitted_by_month = qs.filter(
        status="submitted",
        created_at__date__gte=start_date
    ).extra(
        select={'month': "strftime('%%Y-%%m', created_at)"}
    ).values('month').annotate(count=Count('id')).order_by('month')
    
    # Solicitudes aceptadas por mes
    accepted_by_month = qs.filter(
        status="accepted",
        created_at__date__gte=start_date
    ).extra(
        select={'month': "strftime('%%Y-%%m', created_at)"}
    ).values('month').annotate(count=Count('id')).order_by('month')

    # Convertir datos del gráfico a formato JSON
    import json
    submitted_data_json = json.dumps(list(submitted_by_month))
    accepted_data_json = json.dumps(list(accepted_by_month))

    return render(request, "icts/user_dashboard.html", {
        "drafts": drafts,
        "changes_requested": changes_requested,
        "submitted": submitted,
        "evaluated": evaluated,
        "user_analyses": user_analyses,
        "user_mcf_sessions": user_mcf_sessions,
        "user_imp_sessions": user_imp_sessions,
        "user_vdg_sessions": user_vdg_sessions,
        "submitted_by_month": submitted_by_month,
        "accepted_by_month": accepted_by_month,
        "submitted_data_json": submitted_data_json,
        "accepted_data_json": accepted_data_json,
    })


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
@never_cache
def implant_dashboard(request):
    groups = get_normalized_user_groups(request.user)
    if not user_in_groups(request.user, IMP_TECH_GROUPS, groups) and not request.user.is_superuser:
        raise PermissionDenied
    return render(request, "icts/implant_dashboard.html", {})

# --- Registro ICTS ---
class RegisterICTSView(FormView):
    template_name = "icts/register.html"
    form_class = RegistrationICTSForm
    success_url = reverse_lazy("accounts:login_icts")

    def form_valid(self, form):
        user = form.save()
        send_new_user_registration_notification(user)
        messages.success(self.request, "Tu cuenta ha sido registrada. Un responsable la revisará en un máximo de 48 horas.")
        return super().form_valid(form)

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
@never_cache
def my_proposals(request):
    qs = AccessProposal.objects.filter(applicant=request.user).order_by("-created_at")
    state = request.GET.get("state")
    if state in {"draft", "submitted", "accepted", "rejected", "changes_requested"}:
        qs = qs.filter(status=state)
    return render(request, "icts/my_proposals.html", {"proposals": qs, "state": state})

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_plain_icts_user, raise_exception=True)
def save_technique_draft(request):
    """Vista para guardar borradores de tecnicas individuales"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            technique = data.get('technique')
            form_data = data.get('form_data', {})
            proposal_id = data.get('proposal_id') or "legacy"
            
            if not technique:
                return JsonResponse({'success': False, 'error': 'Tecnica no especificada'})
            
            # Guardar en session o en un modelo temporal
            # Por ahora usamos session
            if 'technique_drafts' not in request.session:
                request.session['technique_drafts'] = {}
            
            drafts = request.session['technique_drafts']
            if isinstance(drafts, dict):
                bucket = drafts.get(str(proposal_id))
                if not isinstance(bucket, dict):
                    bucket = {}
                bucket[technique] = form_data
                drafts[str(proposal_id)] = bucket
                request.session['technique_drafts'] = drafts
            else:
                request.session['technique_drafts'] = {str(proposal_id): {technique: form_data}}
            request.session.modified = True
            
            return JsonResponse({'success': True, 'message': 'Borrador guardado correctamente'})
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Datos JSON invalidos'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Metodo no permitido'})

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_plain_icts_user, raise_exception=True)
def load_technique_draft(request):
    """Vista para cargar borradores de tecnicas individuales"""
    groups = get_normalized_user_groups(request.user)
    if (
        is_reviewer(request.user, groups)
        or is_responsable(request.user, groups)
        or is_manager(request.user, groups)
    ):
        return HttpResponseForbidden()
    if request.method == 'GET':
        technique = request.GET.get('technique')
        proposal_id = request.GET.get('proposal_id') or "legacy"
        
        if not technique:
            return JsonResponse({'success': False, 'error': 'Tecnica no especificada'})
        
        # Cargar desde session
        technique_drafts = request.session.get('technique_drafts', {})
        form_data = {}
        if isinstance(technique_drafts, dict):
            bucket = technique_drafts.get(str(proposal_id))
            if isinstance(bucket, dict):
                form_data = bucket.get(technique, {})
            elif technique in technique_drafts:
                # Compatibilidad con sesiones antiguas planas
                form_data = technique_drafts.get(technique, {})
        
        return JsonResponse({'success': True, 'form_data': form_data})
    
    return JsonResponse({'success': False, 'error': 'Metodo no permitido'})

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_plain_icts_user, raise_exception=True)
def load_previous_proposal(request):
    """Vista para cargar datos de una propuesta anterior"""
    if request.method == 'GET':
        proposal_id = request.GET.get('proposal_id')
        
        if not proposal_id:
            return JsonResponse({'success': False, 'error': 'ID de propuesta no especificado'})
        
        try:
            # Obtener la propuesta anterior del usuario
            status_filter = ['accepted', 'submitted', 'changes_requested', 'rejected']
            previous_proposal = None
            proposal_pk = None
            try:
                proposal_pk = int(proposal_id)
            except (TypeError, ValueError):
                proposal_pk = None

            if proposal_pk is not None:
                previous_proposal = AccessProposal.objects.filter(
                    id=proposal_pk,
                    applicant=request.user,
                    status__in=status_filter,
                ).first()

            if previous_proposal is None:
                previous_proposal = AccessProposal.objects.filter(
                    access_code=proposal_id,
                    applicant=request.user,
                    status__in=status_filter,
                ).first()

            if previous_proposal is None:
                raise AccessProposal.DoesNotExist
            
            # Preparar datos básicos de la propuesta
            proposal_data = {
                'title': previous_proposal.title,
                'scope': previous_proposal.scope,
                'project_name': previous_proposal.project_name,
                'funding_source': previous_proposal.funding_source,
                'organization': previous_proposal.organization,
                'contact_person': previous_proposal.contact_person,
                'email': previous_proposal.email,
                'phone': previous_proposal.phone,
                'start_year': previous_proposal.start_year,
                'end_year': previous_proposal.end_year,
                'previous_experiments': previous_proposal.previous_experiments,
                'references': previous_proposal.references,
            }
            
            # Preparar datos de técnicas
            technique_data = {}
            if previous_proposal.facility_data:
                technique_data = previous_proposal.facility_data
            
            return JsonResponse({
                'success': True, 
                'proposal_data': proposal_data,
                'technique_data': technique_data
            })
            
        except AccessProposal.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Propuesta anterior no encontrada'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
def proposal_create(request):
    facility_data_payload = {}
    facility_data_parsed = None
    if request.method == "POST":
        form = AccessProposalForm(request.POST, request=request)
        formset = ParticipantFormSet(request.POST)  # alias simple
        attachment_formset = AttachmentFormSet(
            request.POST,
            request.FILES,
            prefix="attachments",
        )

        # Si no se renderiza el formset de adjuntos, no lo hacemos bloquear.
        # Detectamos la management form con el prefijo real del formset
        has_attach_mgmt = f"{attachment_formset.prefix}-TOTAL_FORMS" in request.POST

        fd = request.POST.get("facility_data_json")
        if fd is not None:
            facility_data_parsed = _parse_facility_data_json(fd)
            if isinstance(facility_data_parsed, dict):
                facility_data_payload = facility_data_parsed
        logger.debug(
            "facility_data_json size=%s parsed=%s",
            len(fd) if fd is not None else None,
            isinstance(facility_data_parsed, dict),
        )
        logger.debug(
            "facility_data_json size=%s parsed=%s",
            len(fd) if fd is not None else None,
            isinstance(facility_data_parsed, dict),
        )


        if form.is_valid() and formset.is_valid() and (attachment_formset.is_valid() if has_attach_mgmt else True):
            obj = form.save(commit=False)
            obj.applicant = request.user
            if not obj.applicant_is_different:
                obj.contact_person = request.user.get_full_name() or request.user.username
                obj.email = request.user.email
                if hasattr(request.user, "icts_profile") and request.user.icts_profile:
                    obj.organization = request.user.icts_profile.center
            base_facility_payload = facility_data_parsed if isinstance(facility_data_parsed, dict) else {}
            base_facility_payload = _apply_session_technique_drafts(
                request,
                obj,
                base_facility_payload,
                proposal_id="legacy",
            )
            obj.facility_data = _filter_facility_data_by_selection(base_facility_payload, obj)
            obj.save()
            form.save_m2m()

            formset.instance = obj
            formset.save()

            if has_attach_mgmt:
                attachment_formset.instance = obj
                attachment_formset.save()

            messages.success(request, "Propuesta creada como borrador.")
            return redirect("icts:proposal_detail", pk=obj.pk)
        else:
            messages.error(request, "Corrige los errores del formulario.")
    else:
        form = AccessProposalForm(request=request)
        initial_participant = _build_default_participant_initial(request)
        formset = ParticipantFormSet(initial=[initial_participant])
        attachment_formset = AttachmentFormSet(prefix="attachments")

    user_siglas = ensure_user_siglas(request.user)
    next_seq_preview = get_next_user_sequence(request.user)
    preview_date = timezone.now()
    if formset.is_bound:
        participants_count = _count_participants_from_post(request, formset.prefix)
    else:
        participants_count = 1
    
    return render(request, "icts/proposal_form.html", {
        "form": form,
        "formset": formset,                              # ← nombre coherente con la plantilla
        "attachment_formset": attachment_formset,
        "editing": False,
        "initial_facility_data": facility_data_payload if facility_data_parsed is not None else {},
        "user_initials": user_siglas,
        "next_seq_preview": next_seq_preview,
        "preview_month": f"{preview_date.month:02d}",
        "preview_year": f"{preview_date.year % 100:02d}",
        "participants_count": participants_count,
    })

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
@never_cache
def proposal_detail(request, pk):
    groups = get_normalized_user_groups(request.user)
    if is_manager(request.user, groups) and not (
        is_responsable(request.user, groups)
        or is_reviewer(request.user, groups)
        or request.user.is_superuser
    ):
        raise PermissionDenied
    privileged = (
        is_reviewer(request.user, groups)
        or is_responsable(request.user, groups)
        or request.user.is_superuser
    )

    if privileged:
        obj = get_object_or_404(AccessProposal, pk=pk)
    else:
        if user_in_groups(request.user, OLMAT_TECH_GROUPS, groups):
            obj = get_object_or_404(AccessProposal, pk=pk, facility_olmat=True)
        else:
            obj = get_object_or_404(AccessProposal, pk=pk, applicant=request.user)

    reviews = obj.reviews.select_related("reviewer").all()
    decided = obj.reviews.filter(status="submitted").count()
    total_reviews = obj.reviews.count()
    min_required_reviews = getattr(settings, "ICTS_MIN_REVIEWS_REQUIRED", 4)
    required_reviews = min(min_required_reviews, total_reviews)
    submitted_at = obj.submitted_at or obj.created_at
    days_since_submitted = (timezone.now().date() - submitted_at.date()).days
    has_icts_facilities = _has_icts_facilities(obj)
    if has_icts_facilities:
        can_decide = (
            is_responsable(request.user, groups)
            and obj.status == "submitted"
            and (decided >= required_reviews or days_since_submitted >= 10)
        )
    else:
        can_decide = is_responsable(request.user, groups) and obj.status == "submitted"
    # Anonimato para el solicitante: no ver nombres de revisores y
    # no ver evaluaciones hasta que el responsable haya decidido (accepted/rejected).
    is_applicant = obj.applicant_id == request.user.id
    is_staff_role = privileged
    show_reviews_to_applicant = obj.status in ("accepted", "rejected")
    is_reviewer_user = is_reviewer(request.user, groups)
    is_responsable_user = is_responsable(request.user, groups)

    # Ajustar visibilidad según el tipo de usuario
    anon_reviews = []
    if is_applicant and not is_staff_role:
        # Usuario solicitante: solo ver evaluaciones cuando hay decisión final
        if show_reviews_to_applicant:
            completed = obj.reviews.filter(status="submitted").order_by("updated_at", "id")
            reviews = list(completed)
            for i, r in enumerate(completed, start=1):
                anon_reviews.append({"review": r, "alias": f"Revisor {i}"})
        else:
            reviews = []
    elif is_reviewer_user and not is_responsable_user:
        # Revisor: solo ver su propia evaluación
        user_review = obj.reviews.filter(reviewer=request.user).first()
        reviews = [user_review] if user_review else []
    elif is_responsable_user:
        # Responsable: ver todas las evaluaciones
        reviews = obj.reviews.all()
    else:
        # Otros usuarios: no ver evaluaciones
        reviews = []

    review_summary = None
    review_summary_comments = []
    if is_responsable_user:
        completed_reviews = obj.reviews.filter(status="submitted")
        avg_scores = completed_reviews.aggregate(
            avg_scientific=Avg("score_scientific_quality"),
            avg_infrastructure=Avg("score_need_infrastructure"),
            avg_industrial=Avg("score_industrial_potential"),
        )
        review_summary = {
            "avg_scientific": round(avg_scores["avg_scientific"], 1) if avg_scores["avg_scientific"] is not None else None,
            "avg_infrastructure": round(avg_scores["avg_infrastructure"], 1) if avg_scores["avg_infrastructure"] is not None else None,
            "avg_industrial": round(avg_scores["avg_industrial"], 1) if avg_scores["avg_industrial"] is not None else None,
            "completed_count": completed_reviews.count(),
        }
        for review in completed_reviews:
            comment = (review.comments or "").strip()
            if comment:
                review_summary_comments.append(
                    {
                        "reviewer": review.reviewer,
                        "comment": comment,
                        "updated_at": review.updated_at,
                    }
                )

    try:
        olmat_request = obj.olmat_request
    except OLMATRequest.DoesNotExist:
        olmat_request = None

    facility_data_view = _build_facility_data_view(obj.facility_data)
    facility_data_raw = None
    if not facility_data_view and obj.facility_data:
        import json
        try:
            facility_data_raw = json.dumps(obj.facility_data, ensure_ascii=False, indent=2)
        except Exception:
            facility_data_raw = str(obj.facility_data)

    return render(
        request,
        "icts/proposal_detail.html",
        {
            "obj": obj,
            "reviews": reviews,
            "can_decide": can_decide,
            "is_applicant": is_applicant,
            "is_staff_role": is_staff_role,
            "show_reviews_to_applicant": show_reviews_to_applicant,
            "is_responsable_user": is_responsable_user,
            "anon_reviews": anon_reviews,
            "olmat_request": olmat_request,
            "facility_data_view": facility_data_view,
            "facility_data_raw": facility_data_raw,
            "review_summary": review_summary,
            "review_summary_comments": review_summary_comments,
            "days_since_submitted": days_since_submitted,
        }
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
@never_cache
def proposal_edit(request, pk):
    obj = get_object_or_404(AccessProposal, pk=pk, applicant=request.user)
    facility_data_payload = obj.facility_data or {}
    facility_data_parsed = None
    if obj.status not in {"draft", "changes_requested"}:
        messages.error(request, "Solo se pueden editar propuestas en borrador o con cambios solicitados.")
        return redirect("icts:proposal_detail", pk=obj.pk)

    if request.method == "POST":
        form = AccessProposalForm(request.POST, instance=obj, request=request)
        formset = ParticipantFormSet(request.POST, instance=obj)
        attachment_formset = AttachmentFormSet(
            request.POST,
            request.FILES,
            instance=obj,
            prefix="attachments",
        )

        has_attach_mgmt = f"{attachment_formset.prefix}-TOTAL_FORMS" in request.POST

        fd = request.POST.get("facility_data_json")
        if fd is not None:
            facility_data_parsed = _parse_facility_data_json(fd)
            if isinstance(facility_data_parsed, dict):
                facility_data_payload = facility_data_parsed


        if form.is_valid() and formset.is_valid() and (attachment_formset.is_valid() if has_attach_mgmt else True):
            obj = form.save(commit=False)
            if isinstance(facility_data_parsed, dict):
                base_facility_payload = facility_data_parsed
            elif fd is not None:
                base_facility_payload = {}
            else:
                base_facility_payload = obj.facility_data or {}
            base_facility_payload = _apply_session_technique_drafts(
                request,
                obj,
                base_facility_payload,
                proposal_id=obj.pk,
            )
            obj.facility_data = _filter_facility_data_by_selection(base_facility_payload, obj)
            obj.save()
            form.save_m2m()
            formset.save()
            if has_attach_mgmt:
                attachment_formset.save()
            messages.success(request, "Borrador actualizado.")
            return redirect("icts:proposal_detail", pk=obj.pk)

    else:
        form = AccessProposalForm(instance=obj, request=request)
        if obj.participants.count() == 0:
            initial_participant = _build_default_participant_initial(request, proposal=obj)
            formset = ParticipantFormSet(instance=obj, initial=[initial_participant])
        else:
            formset = ParticipantFormSet(instance=obj)
        attachment_formset = AttachmentFormSet(instance=obj, prefix="attachments")

    user_siglas = ensure_user_siglas(request.user)
    next_seq_preview = get_next_user_sequence(request.user)
    preview_date = timezone.now()
    if formset.is_bound:
        participants_count = _count_participants_from_post(request, formset.prefix)
    else:
        participants_count = max(obj.participants.count(), 1)

    return render(
        request,
        "icts/proposal_form.html",
        {
            "form": form,
            "formset": formset,
            "attachment_formset": attachment_formset,
            "editing": True,
            "proposal_id": obj.pk,
            "initial_facility_data": facility_data_payload,
            "user_initials": user_siglas,
            "next_seq_preview": next_seq_preview,
            "preview_month": f"{preview_date.month:02d}",
            "preview_year": f"{preview_date.year % 100:02d}",
            "participants_count": participants_count,
        },
    )

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
@never_cache
def proposal_delete(request, pk):
    """Elimina una propuesta en borrador."""
    obj = get_object_or_404(AccessProposal, pk=pk, applicant=request.user)
    if obj.status != "draft":
        messages.error(request, "Solo se pueden eliminar propuestas en borrador.")
        return redirect("icts:proposal_detail", pk=obj.pk)
    
    if request.method == "POST":
        title = obj.title or f"Propuesta #{obj.id}"
        obj.delete()
        messages.success(request, f"La propuesta '{title}' ha sido eliminada.")
        return redirect("icts:my_proposals")
    
    return render(request, "icts/proposal_confirm_delete.html", {"proposal": obj})

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
@never_cache
def proposal_submit(request, pk):
    """Pasa de 'draft' a 'submitted' y crea tareas de revisión para TODOS los revisores."""
    obj = get_object_or_404(AccessProposal, pk=pk, applicant=request.user)
    if obj.status not in {"draft", "changes_requested"}:
        messages.error(request, "Solo se pueden enviar propuestas en borrador o con cambios solicitados.")
        return redirect("icts:proposal_detail", pk=obj.pk)
    with transaction.atomic():
        locked_qs = AccessProposal.objects
        if connection.features.has_select_for_update:
            locked_qs = locked_qs.select_for_update()
        obj = locked_qs.get(pk=obj.pk)
        if not obj.has_icts_techniques and not obj.facility_olmat:
            messages.error(request, "Debes seleccionar al menos una tecnica antes de enviar.")
            return redirect("icts:proposal_detail", pk=obj.pk)
        missing_steps = _validate_required_steps_for_submit(obj)
        if missing_steps:
            messages.error(
                request,
                "Faltan campos requeridos: " + ", ".join(missing_steps),
            )
            return redirect("icts:proposal_detail", pk=obj.pk)
        imp_errors = _validate_imp_data(obj, obj.facility_data)
        if imp_errors:
            for error in imp_errors:
                messages.error(request, error)
            return redirect("icts:proposal_detail", pk=obj.pk)
        profilometer_errors = (
            _validate_profilometer_data(obj.facility_data)
            if getattr(obj, "facility_profilometer", False)
            else []
        )
        if profilometer_errors:
            for error in profilometer_errors:
                messages.error(request, error)
            return redirect("icts:proposal_detail", pk=obj.pk)
        missing_sections = _require_text_or_ack(obj, request.POST)
        if missing_sections:
            messages.error(
                request,
                "Completa los textos o marca las confirmaciones antes de enviar.",
            )
            return redirect("icts:proposal_detail", pk=obj.pk)
        obj.status = "submitted"

        if not obj.submitted_at:
            obj.submitted_at = timezone.now()

        if obj.user_sequence_number is None:
            profile_qs = ICTSUserProfile.objects
            if connection.features.has_select_for_update:
                profile_qs = profile_qs.select_for_update()
            profile, _ = profile_qs.get_or_create(user=request.user)

            max_seq = (
                AccessProposal.objects.filter(
                    applicant=request.user, user_sequence_number__isnull=False
                )
                .aggregate(max_seq=Max("user_sequence_number"))
                .get("max_seq")
                or 0
            )
            count_no_draft = (
                AccessProposal.objects.filter(applicant=request.user)
                .exclude(status="draft")
                .count()
            )
            base = max(profile.proposal_counter or 0, max_seq, count_no_draft)
            profile.proposal_counter = base + 1
            profile.save(update_fields=["proposal_counter"])
            obj.user_sequence_number = profile.proposal_counter

        if not obj.access_code:
            obj.access_code = build_access_code(obj, None, include_olmat=False)

        update_fields = ["status"]
        if obj.submitted_at:
            update_fields.append("submitted_at")
        if obj.user_sequence_number is not None:
            update_fields.append("user_sequence_number")
        if obj.access_code:
            update_fields.append("access_code")
        obj.save(update_fields=update_fields)

    # Crear solicitud parcial específica de OLMAT para los técnicos
    olmat_request = None
    if getattr(obj, "facility_olmat", False):
        olmat_request, _ = _ensure_olmat_request_from_submission(obj, request)

    # Asigna revisores: crea una ProposalReview 'pending' por cada miembro del grupo 'revisores'
    has_icts_facilities = obj.has_icts_techniques
    reviews_created = False
    if has_icts_facilities:
        from django.contrib.auth.models import Group
        reviewers = Group.objects.filter(name__iexact="revisores").first()
        if reviewers:
            for user in reviewers.user_set.all().distinct():
                ProposalReview.objects.get_or_create(proposal=obj, reviewer=user)
            reviews_created = True

    # Enviar notificaciones
    send_proposal_notification(obj, 'submitted')
    if reviews_created:
        send_proposal_notification(obj, 'review_assigned')

    if obj.is_olmat_only:
        extra_msg = ""
        if olmat_request:
            extra_msg = " Se ha generado la solicitud OLMAT para el equipo tecnico."
        messages.success(request, f"Propuesta OLMAT enviada. No entra en revision ICTS.{extra_msg}")
    elif obj.facility_olmat and olmat_request:
        extra_msg = " y se ha generado la solicitud OLMAT para el equipo tecnico"
        messages.success(request, f"Propuesta enviada a revision{extra_msg}.")
    else:
        messages.success(request, "Propuesta enviada a revision.")
    return redirect("icts:proposal_detail", pk=obj.pk)



@login_required(login_url="/accounts/login/icts/")
@never_cache
def reviewer_inbox(request):
    groups = get_normalized_user_groups(request.user)
    if is_responsable(request.user, groups):
        return redirect("icts:responsable_dashboard")
    if is_manager(request.user, groups):
        return redirect("icts:manager_dashboard")
    if not is_reviewer(request.user, groups):
        raise PermissionDenied
    proposal_filter = _icts_facilities_q(prefix="proposal__")
    base = (
        ProposalReview.objects.select_related("proposal", "proposal__applicant")
        .filter(reviewer=request.user)
        .filter(proposal_filter)
    )
    pending_reviews = base.filter(
        status="draft",
        proposal__status="submitted",
    ).order_by("-proposal__created_at")
    submitted_reviews = base.filter(
        status="submitted",
        proposal__status="submitted",
    ).order_by("-submitted_at")
    pending_mod_request = ProposalReviewModificationRequest.objects.filter(
        review=OuterRef("pk"),
        status="pending",
    )
    submitted_reviews = submitted_reviews.annotate(
        has_pending_mod_request=Exists(pending_mod_request)
    )
    completed_reviews = base.filter(
        proposal__status__in=["accepted", "rejected", "changes_requested"]
    ).order_by("-proposal__created_at")
    return render(
        request,
        "icts/reviewer_inbox.html",
        {
            "pending_reviews": pending_reviews,
            "submitted_reviews": submitted_reviews,
            "completed_reviews": completed_reviews,
        },
    )

@login_required(login_url="/accounts/login/icts/")
@never_cache
def reviewer_dashboard_new(request):
    """Dashboard mejorado del revisor con estadísticas y plazos"""
    groups = get_normalized_user_groups(request.user)
    if is_responsable(request.user, groups):
        return redirect("icts:responsable_dashboard")
    if is_manager(request.user, groups):
        return redirect("icts:manager_dashboard")
    if not is_reviewer(request.user, groups):
        raise PermissionDenied
    from datetime import datetime, timedelta
    proposal_filter = _icts_facilities_q(prefix="proposal__")
    
    # Estadísticas básicas
    # Para revisores: mostrar solo sus evaluaciones
    # Para responsables/managers: mostrar todas las evaluaciones
    base = ProposalReview.objects.filter(
        reviewer=request.user,
    ).filter(
        proposal_filter
    ).select_related("proposal")

    pending_reviews = base.filter(
        status="draft",
        proposal__status="submitted",
    )

    submitted_reviews = base.filter(
        status="submitted",
        proposal__status="submitted",
    )

    completed_reviews = base.filter(
        proposal__status__in=["accepted", "rejected", "changes_requested"],
    )
    
    # Contadores
    pending_count = pending_reviews.count()
    submitted_count = submitted_reviews.count()
    completed_count = completed_reviews.count()
    approved_count = completed_reviews.filter(proposal__status="accepted").count()
    rejected_count = completed_reviews.filter(proposal__status="rejected").count()
    
    # Revisiones pendientes con información de días
    pending_with_days = []
    for review in pending_reviews:
        days_pending = (datetime.now().date() - review.proposal.created_at.date()).days
        is_urgent = days_pending > 7  # Más de 7 días es urgente
        pending_with_days.append({
            'review': review,
            'days_pending': days_pending,
            'is_urgent': is_urgent
        })
    
    urgent_count = sum(1 for item in pending_with_days if item['is_urgent'])
    
    # Revisiones recientes (últimas 5)
    recent_reviews = submitted_reviews.order_by('-updated_at')[:5]
    
    context = {
        'pending_count': pending_count,
        'submitted_count': submitted_count,
        'completed_count': completed_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'urgent_count': urgent_count,
        'pending_reviews': pending_with_days,
        'recent_reviews': recent_reviews,
    }
    
    return render(request, "icts/reviewer_dashboard_new.html", context)

@login_required(login_url="/accounts/login/icts/")
@never_cache
def review_history(request):
    """Historial de evaluaciones del revisor con filtros"""
    from django.core.paginator import Paginator
    from django.db.models import Q

    groups = get_normalized_user_groups(request.user)
    if is_responsable(request.user, groups):
        return redirect("icts:responsable_dashboard")
    if is_manager(request.user, groups):
        return redirect("icts:manager_dashboard")
    if not is_reviewer(request.user, groups):
        raise PermissionDenied
    
    # Obtener todas las evaluaciones del revisor
    reviews = ProposalReview.objects.filter(
        reviewer=request.user,
        status="submitted",
    ).select_related('proposal', 'proposal__applicant').order_by('-updated_at')
    
    # Aplicar filtros
    decision = request.GET.get('decision')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search')
    
    if decision:
        reviews = reviews.filter(decision=decision)
    
    if date_from:
        reviews = reviews.filter(updated_at__date__gte=date_from)
    
    if date_to:
        reviews = reviews.filter(updated_at__date__lte=date_to)
    
    if search:
        reviews = reviews.filter(
            Q(proposal__title__icontains=search) |
            Q(proposal__applicant__username__icontains=search) |
            Q(proposal__applicant__first_name__icontains=search) |
            Q(proposal__applicant__last_name__icontains=search)
        )
    
    # Paginación
    paginator = Paginator(reviews, 10)  # 10 evaluaciones por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'reviews': page_obj,
        'total_reviews': reviews.count(),
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    
    return render(request, "icts/review_history.html", context)


@login_required(login_url="/accounts/login/icts/")
@never_cache
def reviewer_mailbox(request):
    """Stub de bandeja de entrada de mensajes (en desarrollo)."""
    groups = get_normalized_user_groups(request.user)
    if is_responsable(request.user, groups):
        return redirect("icts:responsable_dashboard")
    if is_manager(request.user, groups):
        return redirect("icts:manager_dashboard")
    if not is_reviewer(request.user, groups):
        raise PermissionDenied
    return render(request, "icts/reviewer_mailbox.html", {})


@login_required(login_url="/accounts/login/icts/")
@never_cache
def reviewer_faq(request):
    groups = get_normalized_user_groups(request.user)
    if is_responsable(request.user, groups):
        return redirect("icts:responsable_dashboard")
    if is_manager(request.user, groups):
        return redirect("icts:manager_dashboard")
    if not is_reviewer(request.user, groups):
        raise PermissionDenied
    return render(request, "icts/faq_reviewer.html")

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_responsable, raise_exception=True)
@never_cache
def responsable_dashboard(request):
    """Dashboard del responsable con semáforo de revisiones"""
    from django.contrib.auth import get_user_model
    from sigmaconf.models import MCFSession
    from sigmavdg.models import VDGSession
    from sigmaimp.models import IMPSession

    User = get_user_model()
    base_qs = AccessProposal.objects.filter(_icts_facilities_q())
    submitted_qs = AccessProposal.objects.filter(status="submitted").filter(_icts_facilities_q())
    min_required_reviews = getattr(settings, "ICTS_MIN_REVIEWS_REQUIRED", 4)
    review_completed_filter = Q(reviews__status="submitted")
    proposal_filter = _icts_facilities_q(prefix="proposal__")
    now = timezone.now()
    overdue_threshold = now - timedelta(days=10)
    
    # Estadísticas básicas
    stats = {
        "total": base_qs.count(),
        "draft": base_qs.filter(status="draft").count(),
        "submitted": base_qs.filter(status="submitted").count(),
        "submitted_no_reviews": 0,
        "under_review": 0,
        "ready_for_decision": 0,
        "changes_requested": base_qs.filter(status="changes_requested").count(),
        "approved": base_qs.filter(status="accepted").count(),
        "rejected": base_qs.filter(status="rejected").count(),
    }
    
    # Semáforo de revisiones
    proposals_with_reviews = submitted_qs.annotate(
        total_reviews=Count('reviews'),
        completed_reviews=Count('reviews', filter=review_completed_filter),
    ).annotate(
        required_reviews=Case(
            When(total_reviews__lt=1, then=Value(min_required_reviews)),
            When(total_reviews__lt=min_required_reviews, then=F("total_reviews")),
            default=Value(min_required_reviews),
            output_field=IntegerField(),
        ),
        num_reviews=F("completed_reviews"),
    ).prefetch_related("reviews__reviewer")

    overdue_filter = Q(submitted_at__lte=overdue_threshold) | Q(
        submitted_at__isnull=True, created_at__lte=overdue_threshold
    )
    decidable_filter = Q(completed_reviews__gte=F("required_reviews")) | overdue_filter
    in_review_filter = (
        Q(completed_reviews__gte=1)
        & Q(completed_reviews__lt=F("required_reviews"))
        & ~overdue_filter
    )
    submitted_no_reviews_filter = Q(completed_reviews=0) & ~overdue_filter
    submitted_no_reviews = proposals_with_reviews.filter(submitted_no_reviews_filter).count()
    under_review = proposals_with_reviews.filter(in_review_filter).count()
    ready_for_decision = proposals_with_reviews.filter(decidable_filter).count()
    stats.update(
        {
            "submitted_no_reviews": submitted_no_reviews,
            "under_review": under_review,
            "ready_for_decision": ready_for_decision,
        }
    )
    
    review_buckets = {
        "rojo_0": proposals_with_reviews.filter(completed_reviews=0).count(),
        "amarillo_1_3": proposals_with_reviews.filter(
            completed_reviews__gte=1,
            completed_reviews__lt=F("required_reviews"),
        ).count(),
        "verde_4mas": proposals_with_reviews.filter(
            completed_reviews__gte=F("required_reviews")
        ).count(),
    }
    
    # Propuestas pendientes de decisión (con revisiones suficientes o SLA vencida)
    pendientes_qs = proposals_with_reviews.filter(decidable_filter).order_by('-created_at')[:20]
    pendientes = list(pendientes_qs)
    en_revision_qs = proposals_with_reviews.filter(in_review_filter).order_by(
        "submitted_at", "created_at"
    )
    en_revision = list(en_revision_qs)

    def _add_sla_fields(proposals):
        for proposal in proposals:
            submitted_at = proposal.submitted_at or proposal.created_at or now
            days_since = (now.date() - submitted_at.date()).days
            proposal.days_since_submitted = days_since
            proposal.urgency_level = min(max(days_since, 0), 10)
            if days_since >= 10:
                proposal.age_class = "age-10"
            elif days_since == 9:
                proposal.age_class = "age-9"
            elif days_since == 8:
                proposal.age_class = "age-8"
            elif days_since == 7:
                proposal.age_class = "age-7"
            else:
                proposal.age_class = ""

            completed = [
                review
                for review in proposal.reviews.all()
                if review.status == "submitted"
            ]
            reviewer_names = []
            for review in completed:
                reviewer = review.reviewer
                name = (reviewer.get_full_name() or reviewer.get_username()).strip()
                if name:
                    reviewer_names.append(name)
            proposal.reviewers_done = ", ".join(reviewer_names)
            proposal.can_decide = (
                proposal.completed_reviews >= proposal.required_reviews
                or proposal.days_since_submitted >= 10
            )

    _add_sla_fields(pendientes)
    _add_sla_fields(en_revision)
    
    # Últimas decisiones
    ultimas = base_qs.filter(
        status__in=['accepted', 'rejected', 'changes_requested']
    ).order_by('-created_at')[:10]
    
    # Estadísticas de revisores
    reviewer_stats = []
    reviewers = User.objects.filter(groups__name="revisores")
    for reviewer in reviewers:
        completed = ProposalReview.objects.filter(
            reviewer=reviewer,
            status="submitted",
        ).filter(
            proposal_filter
        ).count()
        pending = ProposalReview.objects.filter(
            reviewer=reviewer,
            status="draft",
        ).filter(
            proposal_filter
        ).count()
        last_review = ProposalReview.objects.filter(
            reviewer=reviewer
        ).filter(
            proposal_filter
        ).order_by('-updated_at').first()
        
        reviewer_stats.append({
            "user": reviewer,
            "completed_reviews": completed,
            "pending_reviews": pending,
            "last_review": last_review.updated_at if last_review else None,
        })

    session_issues = []

    lo3_sessions = (
        MCFSession.objects.filter(status="in_progress")
        .select_related("access_proposal")
        .prefetch_related("samples")
    )
    for session in lo3_sessions:
        missing_fields = []
        samples = list(session.samples.all())
        if not samples:
            missing_fields.append("Muestras")
        else:
            if any(not (sample.identification or "").strip() for sample in samples):
                missing_fields.append("Identificacion de muestra")
            if any(sample.analysis_date is None for sample in samples):
                missing_fields.append("Fecha de analisis")
            if any(
                not (sample.roughness or sample.image_2d or sample.image_3d or sample.thickness)
                for sample in samples
            ):
                missing_fields.append("Medidas realizadas")
        if missing_fields:
            session_issues.append(
                {
                    "lab": "LO3",
                    "code": session.lot_code,
                    "access_code": session.access_proposal.access_code
                    or f"#{session.access_proposal_id}",
                    "status": session.status,
                    "missing_fields": missing_fields,
                    "detail_url": reverse("sigmaconf:mcf_session_detail", args=[session.pk]),
                    "created_at": session.created_at,
                }
            )

    vdg_sessions = (
        VDGSession.objects.filter(status="in_progress")
        .select_related("access_proposal")
        .prefetch_related("samples")
    )
    for session in vdg_sessions:
        missing_fields = []
        samples = list(session.samples.all())
        if not samples:
            missing_fields.append("Muestras")
        else:
            if any(
                not (sample.code or "").strip() and not (sample.material or "").strip()
                for sample in samples
            ):
                missing_fields.append("Identificacion de muestra")
        if not session.received_date:
            missing_fields.append("Fecha de recepcion")
        if not session.irradiation_start_date:
            missing_fields.append("Fecha de irradiacion")
        if not session.report_issue_date and not session.report_delivery_date:
            missing_fields.append("Fecha de emision/entrega informe")
        if missing_fields:
            session_issues.append(
                {
                    "lab": "VDG",
                    "code": session.lot_code,
                    "access_code": session.access_proposal.access_code
                    or f"#{session.access_proposal_id}",
                    "status": session.status,
                    "missing_fields": missing_fields,
                    "detail_url": reverse("sigmavdg:vdg_session_detail", args=[session.pk]),
                    "created_at": session.created_at,
                }
            )

    imp_sessions = (
        IMPSession.objects.filter(status="in_progress")
        .select_related("access_proposal")
        .prefetch_related("samples")
    )
    for session in imp_sessions:
        missing_fields = []
        samples = list(session.samples.all())
        if not samples:
            missing_fields.append("Muestras")
        else:
            if any(not (sample.identification or "").strip() for sample in samples):
                missing_fields.append("Identificacion de muestra")
            if any(sample.implant_date is None for sample in samples):
                missing_fields.append("Fecha de implantacion")
        if missing_fields:
            session_issues.append(
                {
                    "lab": "IMP",
                    "code": session.session_code,
                    "access_code": session.access_proposal.access_code
                    or f"#{session.access_proposal_id}",
                    "status": session.status,
                    "missing_fields": missing_fields,
                    "detail_url": reverse("sigmaimp:imp_session_detail", args=[session.pk]),
                    "created_at": session.created_at,
                }
            )

    session_issues.sort(key=lambda item: item["created_at"], reverse=True)

    return render(request, "icts/responsable_dashboard.html", {
        "stats": stats,
        "review_buckets": review_buckets,
        "pendientes": pendientes,
        "en_revision": en_revision,
        "ultimas": ultimas,
        "reviewer_stats": reviewer_stats,
        "session_issues": session_issues,
    })


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_manager, raise_exception=True)
@never_cache
def manager_dashboard(request):
    """Dashboard para managers con metricas agregadas."""
    from django.contrib.auth import get_user_model
    from django.db.models import Count, Q
    from django.db.models.functions import ExtractYear

    User = get_user_model()
    base_qs = AccessProposal.objects.filter(_icts_facilities_q())

    total_proposals = base_qs.count()
    draft_proposals = base_qs.filter(status="draft").count()
    submitted_proposals = base_qs.filter(status="submitted").count()
    approved_proposals = base_qs.filter(status="accepted").count()
    rejected_proposals = base_qs.filter(status="rejected").count()

    decided_proposals = approved_proposals + rejected_proposals
    approval_rate = round((approved_proposals / decided_proposals * 100) if decided_proposals > 0 else 0, 1)
    rejection_rate = round((rejected_proposals / decided_proposals * 100) if decided_proposals > 0 else 0, 1)

    conversion_rate = round((submitted_proposals / total_proposals * 100) if total_proposals > 0 else 0, 1)
    system_efficiency = round((decided_proposals / submitted_proposals * 100) if submitted_proposals > 0 else 0, 1)

    thirty_days_ago = timezone.now() - timedelta(days=30)
    seven_days_ago = timezone.now() - timedelta(days=7)
    one_day_ago = timezone.now() - timedelta(days=1)

    recent_proposals = base_qs.filter(created_at__gte=thirty_days_ago).count()
    weekly_proposals = base_qs.filter(created_at__gte=seven_days_ago).count()
    daily_proposals = base_qs.filter(created_at__gte=one_day_ago).count()

    monthly_trends = []
    for i in range(12):
        month_start = timezone.now() - timedelta(days=30 * i)
        month_end = month_start + timedelta(days=30)
        count = base_qs.filter(
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        monthly_trends.append({
            "month": month_start.strftime("%Y-%m"),
            "count": count,
        })
    monthly_trends.reverse()

    technique_stats = []
    technique_approval_rates = []
    techniques = [
        ("SEM/EDX", "facility_sem"),
        ("FIB", "facility_sem_fib"),
        ("SIMS", "facility_sims"),
        ("Metrologia de superficies opticas 3D", "facility_confocal"),
        ("Ion Implanter", "facility_imp"),
        ("VDG", "facility_vdg"),
        ("Profilometer", "facility_profilometer"),
    ]

    for name, field in techniques:
        count = base_qs.filter(**{field: True}).count()
        if count > 0:
            approved_count = base_qs.filter(**{field: True}, status="accepted").count()
            technique_approval_rate = round((approved_count / count * 100) if count > 0 else 0, 1)
            percentage = round((count / total_proposals * 100) if total_proposals > 0 else 0, 1)
            technique_stats.append({
                "name": name,
                "count": count,
                "percentage": percentage,
                "approval_rate": technique_approval_rate,
            })
            technique_approval_rates.append({
                "name": name,
                "approval_rate": technique_approval_rate,
            })

    yearly_data = base_qs.annotate(
        year=ExtractYear("created_at"),
    ).values("year").annotate(
        count=Count("id"),
        approved=Count("id", filter=Q(status="accepted")),
        rejected=Count("id", filter=Q(status="rejected")),
    ).order_by("year")

    yearly_stats = []
    for item in yearly_data:
        total_year = item["count"]
        approved_year = item["approved"]
        rejected_year = item["rejected"]
        total_decided = approved_year + rejected_year
        year_approval_rate = round((approved_year / total_decided * 100) if total_decided > 0 else 0, 1)
        yearly_stats.append({
            "year": str(item["year"]),
            "count": total_year,
            "approved": approved_year,
            "rejected": rejected_year,
            "approval_rate": year_approval_rate,
            "percentage": round((total_year / total_proposals * 100) if total_proposals > 0 else 0, 1),
        })

    center_stats = []
    if hasattr(User, "icts_profile"):
        center_data = User.objects.filter(
            icts_profile__center__isnull=False,
            icts_profile__center__gt="",
        ).values("icts_profile__center").annotate(
            user_count=Count("id"),
            proposal_count=Count("icts_proposals", filter=_icts_facilities_q(prefix="icts_proposals__")),
        ).order_by("-proposal_count")[:10]

        for center in center_data:
            avg_per_user = round(center["proposal_count"] / center["user_count"], 1) if center["user_count"] > 0 else 0
            center_stats.append({
                "name": center["icts_profile__center"],
                "users": center["user_count"],
                "proposals": center["proposal_count"],
                "avg_per_user": avg_per_user,
            })

    active_researchers = User.objects.filter(is_active=True, groups__name="icts_users").count()
    reviewers_count = User.objects.filter(groups__name="revisores").count()
    responsables_count = User.objects.filter(groups__name="responsables").count()
    managers_count = User.objects.filter(groups__name="managers").count()

    if len(monthly_trends) >= 2:
        growth_rate = round(
            ((monthly_trends[-1]["count"] - monthly_trends[-2]["count"]) / monthly_trends[-2]["count"] * 100)
            if monthly_trends[-2]["count"] > 0 else 0,
            1,
        )
    else:
        growth_rate = 0

    return render(request, "icts/manager_dashboard.html", {
        "total_proposals": total_proposals,
        "draft_proposals": draft_proposals,
        "submitted_proposals": submitted_proposals,
        "approved_proposals": approved_proposals,
        "rejected_proposals": rejected_proposals,
        "decided_proposals": decided_proposals,
        "approval_rate": approval_rate,
        "rejection_rate": rejection_rate,
        "conversion_rate": conversion_rate,
        "system_efficiency": system_efficiency,
        "growth_rate": growth_rate,
        "daily_proposals": daily_proposals,
        "monthly_trends": monthly_trends,
        "technique_stats": technique_stats,
        "technique_approval_rates": technique_approval_rates,
        "yearly_stats": yearly_stats,
        "center_stats": center_stats,
        "active_researchers": active_researchers,
        "reviewers_count": reviewers_count,
        "responsables_count": responsables_count,
        "managers_count": managers_count,
    })

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_manager, raise_exception=True)
def export_manager_data(request):
    """Exportar datos agregados del manager a Excel."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from django.http import HttpResponse
    from django.db.models import Count, Q
    from django.db.models.functions import ExtractYear, ExtractMonth

    export_type = request.GET.get("type", "summary")
    include_olmat = request.GET.get("include_olmat") == "1"
    safe_types = {"summary", "temporal", "techniques"}
    if export_type not in safe_types:
        return HttpResponseBadRequest("Tipo de exportacion no permitido.")

    wb = openpyxl.Workbook()

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    def _apply_headers(sheet, headers):
        for col, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = border

    base_qs = AccessProposal.objects.all()
    if not include_olmat:
        base_qs = base_qs.filter(_icts_facilities_q())

    if export_type == "summary":
        ws = wb.active
        ws.title = "Resumen"
        _apply_headers(ws, ["Metrica", "Valor"])

        total_proposals = base_qs.count()
        draft_proposals = base_qs.filter(status="draft").count()
        submitted_proposals = base_qs.filter(status="submitted").count()
        accepted_proposals = base_qs.filter(status="accepted").count()
        rejected_proposals = base_qs.filter(status="rejected").count()

        decided_proposals = accepted_proposals + rejected_proposals
        approval_rate = round((accepted_proposals / decided_proposals * 100) if decided_proposals > 0 else 0, 1)
        rejection_rate = round((rejected_proposals / decided_proposals * 100) if decided_proposals > 0 else 0, 1)
        conversion_rate = round((submitted_proposals / total_proposals * 100) if total_proposals > 0 else 0, 1)

        monthly_trends = []
        for i in range(12):
            month_start = timezone.now() - timedelta(days=30 * i)
            month_end = month_start + timedelta(days=30)
            count = base_qs.filter(created_at__gte=month_start, created_at__lt=month_end).count()
            monthly_trends.append({"month": month_start.strftime("%Y-%m"), "count": count})
        monthly_trends.reverse()

        if len(monthly_trends) >= 2:
            growth_rate = round(
                ((monthly_trends[-1]["count"] - monthly_trends[-2]["count"]) / monthly_trends[-2]["count"] * 100)
                if monthly_trends[-2]["count"] > 0 else 0,
                1,
            )
        else:
            growth_rate = 0

        metrics = [
            ("Total propuestas", total_proposals),
            ("Borradores", draft_proposals),
            ("Enviadas", submitted_proposals),
            ("Aprobadas", accepted_proposals),
            ("Rechazadas", rejected_proposals),
            ("Tasa aprobacion (%)", approval_rate),
            ("Tasa rechazo (%)", rejection_rate),
            ("Conversion (%)", conversion_rate),
            ("Crecimiento mensual (%)", growth_rate),
        ]

        for row, (label, value) in enumerate(metrics, 2):
            label_cell = ws.cell(row=row, column=1, value=label)
            label_cell.border = border
            value_cell = ws.cell(row=row, column=2, value=value)
            value_cell.border = border

    elif export_type == "techniques":
        ws = wb.active
        ws.title = "Tecnicas"
        _apply_headers(ws, ["Tecnica", "Solicitudes", "Aprobadas", "Tasa aprobacion (%)"])

        techniques = [
            ("SEM/EDX", "facility_sem"),
            ("FIB", "facility_sem_fib"),
            ("SIMS", "facility_sims"),
            ("Metrologia de superficies opticas 3D", "facility_confocal"),
            ("Ion Implanter", "facility_imp"),
            ("VDG", "facility_vdg"),
            ("Profilometer", "facility_profilometer"),
        ]

        row = 2
        for name, field in techniques:
            count = base_qs.filter(**{field: True}).count()
            approved = base_qs.filter(**{field: True}, status="accepted").count()
            approval_rate = round((approved / count * 100) if count > 0 else 0, 1)
            for col, value in enumerate([name, count, approved, approval_rate], 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = border
            row += 1

        if include_olmat:
            count = base_qs.filter(facility_olmat=True).count()
            approved = base_qs.filter(facility_olmat=True, status="accepted").count()
            approval_rate = round((approved / count * 100) if count > 0 else 0, 1)
            for col, value in enumerate(["OLMAT", count, approved, approval_rate], 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = border

    elif export_type == "temporal":
        ws = wb.active
        ws.title = "Temporal"
        _apply_headers(ws, ["Ano", "Mes", "Propuestas", "Aprobadas", "Rechazadas", "Tasa aprobacion (%)"])

        temporal_data = base_qs.annotate(
            year=ExtractYear("created_at"),
            month=ExtractMonth("created_at"),
        ).values("year", "month").annotate(
            total=Count("id"),
            approved=Count("id", filter=Q(status="accepted")),
            rejected=Count("id", filter=Q(status="rejected")),
        ).order_by("year", "month")

        for row, data in enumerate(temporal_data, 2):
            total = data["total"]
            approved = data["approved"]
            rejected = data["rejected"]
            approval_rate = round((approved / (approved + rejected) * 100) if (approved + rejected) > 0 else 0, 1)
            row_data = [
                data["year"],
                data["month"],
                total,
                approved,
                rejected,
                approval_rate,
            ]
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = border

    for column in ws.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width

    for row in ws.iter_rows():
        for cell in row:
            if not cell.border:
                cell.border = border

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="icts_analytics_{export_type}_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx"'
    )

    wb.save(response)
    return response

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_manager, raise_exception=True)
def manager_export_page(request):
    """Página de exportación de datos para managers"""
    return render(request, "icts/manager_export.html")


@login_required(login_url="/accounts/login/icts/")
@never_cache
def review_start(request, pk):
    groups = get_normalized_user_groups(request.user)
    if is_responsable(request.user, groups):
        return redirect("icts:responsable_dashboard")
    if not is_reviewer(request.user, groups):
        raise PermissionDenied
    obj = get_object_or_404(AccessProposal, pk=pk)
    if obj.status not in {"submitted", "accepted", "rejected", "changes_requested"}:
        return HttpResponseForbidden("La propuesta aun no esta lista para revision.")
    if not obj.has_icts_techniques:
        messages.error(request, "Esta propuesta es solo OLMAT y no entra en revision ICTS.")
        return redirect("icts:reviewer_inbox")
    review, _ = ProposalReview.objects.get_or_create(
        proposal=obj,
        reviewer=request.user,
    )
    readonly = review.status == "submitted" or obj.status != "submitted"

    if request.method == "POST":
        if readonly:
            return HttpResponseForbidden("Revision ya enviada.")
        form = ProposalReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.status = "draft"
            review.submitted_at = None
            review.draft_saved_at = timezone.now()
            review.save()
            messages.success(request, "Borrador guardado.")
            return redirect("icts:reviewer_inbox")
        else:
            messages.error(request, "Corrige los errores del formulario.")
    else:
        form = ProposalReviewForm(instance=review)
    readonly = review.status == "submitted" or obj.status != "submitted"

    return render(request, "icts/review_form.html", {
        "proposal": obj,
        "form": form,
        "review": review,
        "readonly": readonly,
    })


@login_required(login_url="/accounts/login/icts/")
@never_cache
@require_POST
def review_send(request, pk):
    groups = get_normalized_user_groups(request.user)
    if is_responsable(request.user, groups):
        return redirect("icts:responsable_dashboard")
    if is_manager(request.user, groups):
        return redirect("icts:manager_dashboard")
    if not is_reviewer(request.user, groups):
        raise PermissionDenied
    proposal = get_object_or_404(AccessProposal, pk=pk)
    if not proposal.has_icts_techniques:
        messages.error(request, "Esta propuesta es solo OLMAT y no entra en revision ICTS.")
        return redirect("icts:reviewer_inbox")
    review = get_object_or_404(ProposalReview, proposal=proposal, reviewer=request.user)
    if proposal.status != "submitted":
        return HttpResponseBadRequest("La propuesta ya tiene una decision final.")
    if review.status != "draft":
        return HttpResponseBadRequest("La revision ya fue enviada.")
    if review.draft_saved_at is None:
        messages.error(request, "Guarda la evaluacion antes de enviarla.")
        return redirect("icts:reviewer_inbox")
    if (
        review.feasibility_ok is None
        or review.score_scientific_quality is None
        or review.score_need_infrastructure is None
        or review.score_industrial_potential is None
        or review.decision not in {"approve", "request_changes", "reject"}
    ):
        messages.error(request, "Completa todos los campos obligatorios antes de enviar.")
        return redirect("icts:review_start", pk=proposal.pk)
    review.status = "submitted"
    review.submitted_at = timezone.now()
    review.save(update_fields=["status", "submitted_at"])
    send_proposal_notification(proposal, "review_completed")
    messages.success(
        request,
        "Evaluacion enviada. No podras modificarla salvo reapertura por responsable.",
    )
    return redirect("icts:reviewer_inbox")


@login_required(login_url="/accounts/login/icts/")
@never_cache
@require_POST
def review_request_modify(request, pk):
    groups = get_normalized_user_groups(request.user)
    if is_responsable(request.user, groups):
        return redirect("icts:responsable_dashboard")
    if is_manager(request.user, groups):
        return redirect("icts:manager_dashboard")
    if not is_reviewer(request.user, groups):
        raise PermissionDenied
    proposal = get_object_or_404(AccessProposal, pk=pk)
    review = get_object_or_404(ProposalReview, proposal=proposal, reviewer=request.user)
    if review.status != "submitted":
        return HttpResponseBadRequest("La revision no esta enviada.")
    if proposal.status != "submitted":
        return HttpResponseBadRequest("La propuesta ya tiene una decision final.")
    message = (request.POST.get("message") or "").strip()
    if not message:
        messages.error(request, "Debes indicar el motivo de la solicitud.")
        return redirect("icts:reviewer_inbox")
    if ProposalReviewModificationRequest.objects.filter(
        review=review, status="pending"
    ).exists():
        messages.warning(request, "Ya tienes una solicitud pendiente.")
        return redirect("icts:reviewer_inbox")
    ProposalReviewModificationRequest.objects.create(
        review=review,
        requester=request.user,
        message=message,
    )
    messages.success(request, "Solicitud enviada al responsable.")
    return redirect("icts:reviewer_inbox")


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_responsable, raise_exception=True)
@never_cache
def responsable_review_messages(request):
    pending_requests = ProposalReviewModificationRequest.objects.select_related(
        "review",
        "review__proposal",
        "requester",
    ).filter(
        status="pending"
    ).order_by("-created_at")
    return render(
        request,
        "icts/responsable_review_messages.html",
        {"pending_requests": pending_requests},
    )


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_responsable, raise_exception=True)
@never_cache
@require_POST
def approve_review_mod_request(request, request_id):
    mod_request = get_object_or_404(
        ProposalReviewModificationRequest,
        pk=request_id,
        status="pending",
    )
    now = timezone.now()
    with transaction.atomic():
        mod_request.status = "approved"
        mod_request.resolved_by = request.user
        mod_request.resolved_at = now
        mod_request.save(update_fields=["status", "resolved_by", "resolved_at"])
        review = mod_request.review
        review.status = "draft"
        review.submitted_at = None
        review.reopened_at = now
        review.draft_saved_at = None
        review.save(update_fields=["status", "submitted_at", "reopened_at", "draft_saved_at"])
    messages.success(request, "Solicitud aprobada. Revision reabierta.")
    return redirect("icts:responsable_review_messages")


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_responsable, raise_exception=True)
@never_cache
@require_POST
def deny_review_mod_request(request, request_id):
    mod_request = get_object_or_404(
        ProposalReviewModificationRequest,
        pk=request_id,
        status="pending",
    )
    now = timezone.now()
    mod_request.status = "denied"
    mod_request.resolved_by = request.user
    mod_request.resolved_at = now
    mod_request.save(update_fields=["status", "resolved_by", "resolved_at"])
    messages.success(request, "Solicitud denegada.")
    return redirect("icts:responsable_review_messages")
@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_responsable, raise_exception=True)
@never_cache
def proposal_decide(request, pk):
    obj = get_object_or_404(AccessProposal, pk=pk)
    if request.method == "POST":
        decision = request.POST.get("final_decision")
        responsable_comment = (request.POST.get("responsable_comment") or "").strip()
        if decision not in {"accepted", "rejected", "changes_requested"}:
            messages.error(request, "Seleccion invalida.")
            return redirect("icts:proposal_detail", pk=obj.pk)
        if decision == "changes_requested" and not responsable_comment:
            messages.error(request, "Debes indicar los cambios solicitados.")
            return redirect("icts:proposal_detail", pk=obj.pk)
        if obj.status == "submitted" and _has_icts_facilities(obj):
            total_reviews = obj.reviews.count()
            min_required_reviews = getattr(settings, "ICTS_MIN_REVIEWS_REQUIRED", 4)
            required_reviews = min(min_required_reviews, total_reviews)
            decided = obj.reviews.filter(status="submitted").count()
            submitted_at = obj.submitted_at or obj.created_at or timezone.now()
            days_since_submitted = (timezone.now().date() - submitted_at.date()).days
            if decided < required_reviews and days_since_submitted < 10:
                messages.error(
                    request,
                    "No se puede decidir hasta tener suficientes revisiones o 10 dias desde el envio.",
                )
                return redirect("icts:proposal_detail", pk=obj.pk)
        obj.status = decision
        update_fields = ["status"]
        if decision == "changes_requested":
            obj.responsable_comment = responsable_comment
            update_fields.append("responsable_comment")
        elif obj.responsable_comment:
            obj.responsable_comment = ""
            update_fields.append("responsable_comment")
        if decision == "rejected":
            obj.access_code = build_rejected_code(obj)
            update_fields.append("access_code")
        # Generar access_code solo al aprobar y si esta vacio
        if decision == "accepted" and not obj.access_code:
            include_olmat_in_code = not getattr(obj, "facility_olmat", False)
            obj.access_code = build_access_code(obj, None, include_olmat=include_olmat_in_code)  # El algoritmo se encarga de generar las siglas
            update_fields.append("access_code")
        obj.save(update_fields=update_fields)
        # Enviar notificacion de decision final
        send_proposal_notification(obj, 'decision_made')
        messages.success(request, f"Decision final registrada: {obj.get_status_display()}.")
        return redirect("icts:proposal_detail", pk=obj.pk)
    return HttpResponseForbidden("Metodo no permitido")


# ========= GESTIÓN DE USUARIOS =========

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_responsable, raise_exception=True)
@never_cache
def pending_users(request):
    """Vista para mostrar usuarios pendientes de validación"""
    from django.contrib.auth import get_user_model
    from .models import ICTSUserProfile
    
    User = get_user_model()
    
    # Usuarios inactivos con perfil ICTS
    pending_users = User.objects.filter(
        is_active=False,
        icts_profile__isnull=False
    ).select_related('icts_profile').order_by('-date_joined')
    
    # Estadísticas
    pending_count = pending_users.count()
    validated_today = User.objects.filter(
        is_active=True,
        date_joined__date=timezone.now().date()
    ).count()
    total_users = User.objects.count()
    
    return render(request, "icts/pending_users.html", {
        "pending_users": pending_users,
        "pending_count": pending_count,
        "validated_today": validated_today,
        "total_users": total_users,
    })


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_responsable, raise_exception=True)
@never_cache
def users_admin(request):
    """Vista para administración completa de usuarios"""
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    
    User = get_user_model()
    
    # Parámetros de ordenación
    sort = request.GET.get('sort', 'joined')
    direction = request.GET.get('dir', 'desc')
    
    # Construir ordenación
    order_field = {
        'name': 'first_name',
        'email': 'email',
        'joined': 'date_joined',
        'last_login': 'last_login',
        'active': 'is_active',
        'staff': 'is_staff',
    }.get(sort, 'date_joined')
    
    if direction == 'asc':
        order_field = order_field
    else:
        order_field = f'-{order_field}'
    
    # Obtener usuarios
    users_list = User.objects.all().order_by(order_field)
    
    # Usuarios pendientes
    pending_users = User.objects.filter(
        is_active=False,
        icts_profile__isnull=False
    ).select_related('icts_profile').order_by('-date_joined')
    
    # Estadísticas
    total_users = User.objects.count()
    pending_count = pending_users.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = total_users - active_users
    staff_users = User.objects.filter(is_staff=True).count()
    
    return render(request, "icts/users_admin.html", {
        "users_list": users_list,
        "pending_users": pending_users,
        "total_users": total_users,
        "pending_count": pending_count,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "staff_users": staff_users,
        "sort": sort,
        "dir": direction,
    })


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_responsable, raise_exception=True)
@require_POST
@never_cache
def approve_user(request, user_id):
    """Aprobar un usuario pendiente"""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    user = get_object_or_404(User, id=user_id)
    if not hasattr(user, "icts_profile"):
        raise Http404
    
    if user.is_active:
        messages.warning(request, "Este usuario ya está activo.")
    else:
        user.is_active = True
        user.save()
        user.icts_profile.validated = True
        user.icts_profile.save(update_fields=["validated"])
        # Enviar notificación de aprobación
        send_user_approval_notification(user)
        messages.success(request, f"Usuario {user.username} ha sido aprobado y activado.")
    
    return redirect("icts:pending_users")


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_responsable, raise_exception=True)
@require_POST
@never_cache
def reject_user(request, user_id):
    """Rechazar un usuario pendiente"""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    user = get_object_or_404(User, id=user_id)
    if not hasattr(user, "icts_profile"):
        raise Http404
    
    username = user.username
    user.delete()
    messages.success(request, f"Usuario {username} ha sido rechazado y eliminado.")
    
    return redirect("icts:pending_users")


FACILITY_LABELS = {
    "van-der-graaff": "Van der Graaff",
    "sem-edx": "SEM/EDX",
    "fib": "FIB",
    "implantador": "Implantador",
    "sims": "SIMS",
    "confocal": "Metrolog\u00eda de superficies \u00f3pticas 3D",
    "profilometer": "Perfilómetro",
    "corrosion": "Corrosión",
    "olmat": "OLMAT",
}

def facility_info(request, slug):
    label = FACILITY_LABELS.get(slug, slug.replace("-", " ").title())
    
    # Mapeo de slugs a templates específicos
    facility_templates = {
        "van-der-graaff": "icts/facilities/_van_der_graaff.html",
        "sem-fib": "icts/facilities/_SEM_FIB.html", 
        "sem-edx": "icts/facilities/_SEM_FIB.html",  # Mismo template para SEM/EDX
        "fib": "icts/facilities/_SEM_FIB.html",      # Mismo template para FIB
        "sims": "icts/facilities/_SIMS.html",
        "implantador": "icts/facilities/_implantador.html",
        "olmat": "icts/facilities/_OLMAT.html",
        "confocal": "icts/facilities/_confocal.html",
        "profilometer": "icts/facilities/_profilometer.html",
    }
    
    template_name = facility_templates.get(slug)
    
    return render(request, "icts/facility_info.html", {
        "facility": label, 
        "slug": slug,
        "facility_template": template_name
    })

@never_cache
def proposal_evaluation(request):
    return render(request, "icts/proposal_evaluation.html")

# ========= VISTAS PARA CONFIGURACIÓN DE TÉCNICAS INDIVIDUALES =========

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
def tech_sem_config(request):
    """Vista para configurar SEM/EDX"""
    return render(request, "icts/tech_config/sem.html", {
        "tech_name": "SEM/EDX",
        "tech_slug": "sem",
        "form_template": "icts/forms/_sem.html"
    })

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
def tech_fib_config(request):
    """Vista para configurar FIB"""
    return render(request, "icts/tech_config/fib.html", {
        "tech_name": "FIB",
        "tech_slug": "fib", 
        "form_template": "icts/forms/_fib.html"
    })

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
def tech_imp_config(request):
    """Vista para configurar Ion Implanter"""
    return render(request, "icts/tech_config/imp.html", {
        "tech_name": "Ion Implanter",
        "tech_slug": "imp",
        "form_template": "icts/forms/_imp.html"
    })

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
def tech_sims_config(request):
    """Vista para configurar SIMS"""
    return render(request, "icts/tech_config/sims.html", {
        "tech_name": "SIMS",
        "tech_slug": "sims",
        "form_template": "icts/forms/_sims.html"
    })

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
def tech_confocal_config(request):
    """Vista para configurar LO3"""
    return render(request, "icts/tech_config/confocal.html", {
        "tech_name": "Metrolog\u00eda de superficies \u00f3pticas 3D",
        "tech_slug": "confocal",
        "form_template": "icts/forms/_confocal.html"
    })

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
def tech_olmat_config(request):
    """Vista para configurar OLMAT"""
    return render(request, "icts/tech_config/olmat.html", {
        "tech_name": "OLMAT",
        "tech_slug": "olmat",
        "form_template": "icts/forms/_olmat.html"
    })

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(lambda u: user_in_groups(u, OLMAT_TECH_GROUPS) or is_responsable(u), raise_exception=True)
def olmat_dashboard(request):
    """Panel para técnicos OLMAT: propuestas aceptadas y solicitudes."""
    proposals = (
        AccessProposal.objects
        .filter(status="accepted", facility_olmat=True)
        .select_related("applicant")
        .order_by("-created_at")
    )
    olmat_requests = (
        OLMATRequest.objects
        .select_related("proposal__applicant")
        .order_by("-created_at")
    )

    pending_proposals = [p for p in proposals if not hasattr(p, "olmat_request")]

    stats = {
        "accepted_proposals": proposals.count(),
        "pending_proposals": len(pending_proposals),
        "total_requests": olmat_requests.count(),
        "pending_requests": olmat_requests.filter(status__in=["pending", "under_review"]).count(),
    }

    return render(request, "icts/olmat_dashboard.html", {
        "proposals": proposals,
        "pending_proposals": pending_proposals,
        "olmat_requests": olmat_requests[:10],
        "stats": stats,
    })

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
def tech_vdg_config(request):
    """Vista para configurar VDG"""
    return render(request, "icts/tech_config/vdg.html", {
        "tech_name": "VDG",
        "tech_slug": "vdg",
        "form_template": "icts/forms/_vdg.html"
    })


# ========= VISTAS ESPECÍFICAS PARA OLMAT =========

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
def olmat_request_create(request, proposal_id):
    """Crear solicitud específica de OLMAT para una propuesta"""
    groups = get_normalized_user_groups(request.user)
    can_manage = user_in_groups(request.user, OLMAT_TECH_GROUPS, groups) or is_responsable(request.user, groups)

    if can_manage:
        proposal = get_object_or_404(AccessProposal, pk=proposal_id)
    else:
        proposal = get_object_or_404(AccessProposal, pk=proposal_id, applicant=request.user)
    
    if not proposal.facility_olmat:
        messages.error(request, "Esta propuesta no incluye acceso a OLMAT.")
        return redirect("icts:proposal_detail", pk=proposal_id)
    
    # Verificar si ya existe una solicitud OLMAT
    if hasattr(proposal, 'olmat_request'):
        messages.info(request, "Ya existe una solicitud OLMAT para esta propuesta.")
        return redirect("icts:olmat_request_detail", request_id=proposal.olmat_request.id)

    if request.method == "POST":
        form = OLMATRequestForm(request.POST)
        if form.is_valid():
            olmat_request = form.save(commit=False)
            olmat_request.proposal = proposal
            olmat_request.save()
            if not olmat_request.access_code:
                olmat_request.access_code = build_olmat_access_code(proposal, olmat_request)
                olmat_request.save(update_fields=["access_code"])
            messages.success(request, "Solicitud OLMAT creada exitosamente.")
            return redirect("icts:olmat_request_detail", request_id=olmat_request.id)
    else:
        initial = {
            "proponent_name": proposal.contact_person or proposal.applicant.get_full_name() or proposal.applicant.username,
            "proponent_affiliation": proposal.organization or getattr(getattr(proposal.applicant, "icts_profile", None), "center", ""),
            "activity_description": proposal.scope,
        }
        form = OLMATRequestForm(initial=initial)
    
    return render(request, "icts/olmat_request_form.html", {
        "form": form,
        "proposal": proposal,
        "title": "Nueva solicitud OLMAT"
    })


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
def olmat_request_detail(request, request_id):
    """Ver detalles de una solicitud OLMAT"""
    olmat_request = get_object_or_404(OLMATRequest, pk=request_id)

    if not olmat_request.access_code:
        olmat_request.access_code = build_olmat_access_code(olmat_request.proposal, olmat_request)
        olmat_request.save(update_fields=["access_code"])
    
    # Verificar permisos
    if not (request.user == olmat_request.proposal.applicant or 
            user_in_groups(request.user, OLMAT_TECH_GROUPS) or
            is_responsable(request.user)):
        return HttpResponseForbidden()
    
    return render(request, "icts/olmat_request_detail.html", {
        "olmat_request": olmat_request
    })


@login_required(login_url="/accounts/login/icts/")
@user_passes_test(lambda u: user_in_groups(u, OLMAT_TECH_GROUPS) or is_responsable(u), raise_exception=True)
def olmat_requests_list(request):
    """Lista de solicitudes OLMAT para técnicos"""
    requests = OLMATRequest.objects.select_related('proposal__applicant').order_by('-created_at')
    
    # Filtrar por estado si se especifica
    status_filter = request.GET.get('status')
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    return render(request, "icts/olmat_requests_list.html", {
        "olmat_requests": requests,
        "status_choices": OLMATRequest.STATUS_CHOICES,
        "current_status": status_filter
    })


@login_required(login_url="/accounts/login/icts/")
def olmat_request_evaluate(request, request_id):
    """Evaluar una solicitud OLMAT"""
    olmat_request = get_object_or_404(OLMATRequest, pk=request_id)

    groups = get_normalized_user_groups(request.user)
    if not (user_in_groups(request.user, OLMAT_TECH_GROUPS, groups) or is_responsable(request.user, groups)):
        return HttpResponseForbidden()

    if not olmat_request.access_code:
        olmat_request.access_code = build_olmat_access_code(olmat_request.proposal, olmat_request)
        olmat_request.save(update_fields=["access_code"])
    
    if request.method == "POST":
        form = OLMATEvaluationForm(request.POST, instance=olmat_request)
        if form.is_valid():
            olmat_request = form.save(commit=False)
            olmat_request.evaluated_at = timezone.now()
            olmat_request.save()
            messages.success(request, "Evaluación de solicitud OLMAT actualizada.")
            return redirect("icts:olmat_request_detail", request_id=olmat_request.id)
    else:
        form = OLMATEvaluationForm(instance=olmat_request)
    
    return render(request, "icts/olmat_request_evaluate.html", {
        "form": form,
        "olmat_request": olmat_request
    })

@login_required(login_url="/accounts/login/icts/")
@user_passes_test(is_icts_user, raise_exception=True)
def tech_profilometer_config(request):
    """Vista para configurar Profilometer"""
    return render(request, "icts/tech_config/profilometer.html", {
        "tech_name": "Profilometer",
        "tech_slug": "profilometer",
        "form_template": "icts/forms/_profilometer.html"
    })
