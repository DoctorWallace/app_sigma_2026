import json
from io import BytesIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from icts.models import AccessProposal
from sigmaconf.models import MCFSession, MCFSampleRecord


def _create_user(username, groups=None):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    for name in groups or []:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _set_icts_session(client):
    session = client.session
    session["module"] = "icts"
    session.save()


def _create_session(applicant, technician):
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="LO3 Quality Template",
        status="accepted",
        facility_confocal=True,
        access_code="ACC-LO3-TPL",
        facility_data={"confocal": {}},
    )
    session = MCFSession.objects.create(access_proposal=proposal, technician=technician)
    MCFSampleRecord.objects.create(
        session=session,
        sequence=1,
        source="proposal",
        identification="S-001",
        analysis_date=timezone.now().date(),
        roughness=True,
    )
    return session


def _load_quality_mapping(settings, name):
    mapping_path = (
        Path(settings.BASE_DIR)
        / "quality_templates"
        / "lo3"
        / "REV001"
        / name
    )
    return json.loads(mapping_path.read_text(encoding="utf-8"))


def _assert_fragment_in_pdf(content, fragment):
    normalized_fragment = "".join(fragment.split())
    for encoding in ("utf-8", "latin-1"):
        try:
            decoded = content.decode(encoding)
        except UnicodeDecodeError:
            continue
        if normalized_fragment in "".join(decoded.split()):
            return
    assert False, f"Fragmento no encontrado en PDF: {fragment}"


@pytest.mark.django_db
def test_mcf_export_excel_headers_match_quality_template(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    applicant = _create_user("lo3_tpl_applicant", ["icts_users"])
    technician = _create_user("lo3_tpl_tech", ["confocal_technicians"])
    session = _create_session(applicant, technician)

    client.force_login(technician)
    _set_icts_session(client)

    response = client.get(reverse("sigmaconf:mcf_export_excel", args=[session.pk]))
    assert response.status_code == 200

    mapping = _load_quality_mapping(settings, "mcf_register_mapping.json")
    expected_headers = mapping["headers"]

    workbook = load_workbook(BytesIO(response.content))
    sheet = workbook.active
    actual_headers = [cell.value for cell in sheet[1]]

    assert actual_headers == expected_headers


@pytest.mark.django_db
def test_mcf_notice_pdf_matches_quality_template(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    applicant = _create_user("lo3_tpl_applicant_pdf", ["icts_users"])
    technician = _create_user("lo3_tpl_tech_pdf", ["confocal_technicians"])
    session = _create_session(applicant, technician)

    client.force_login(technician)
    _set_icts_session(client)

    response = client.post(reverse("sigmaconf:mcf_finish_session", args=[session.pk]))
    assert response.status_code == 302

    session.refresh_from_db()
    assert session.notice_pdf

    mapping = _load_quality_mapping(settings, "notice_pdf_mapping.json")
    replacements = {
        "{lot_code}": session.lot_code,
        "{access_code}": session.access_proposal.access_code,
    }

    with session.notice_pdf.open("rb") as handle:
        content = handle.read()

    for fragment in mapping["required_fragments"]:
        for key, value in replacements.items():
            fragment = fragment.replace(key, value)
        _assert_fragment_in_pdf(content, fragment)

    for fragment in mapping["forbidden_fragments"]:
        assert fragment.encode("utf-8") not in content
