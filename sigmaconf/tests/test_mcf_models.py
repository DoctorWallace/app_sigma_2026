import re

import pytest
from django.contrib.auth import get_user_model

from icts.models import AccessProposal
from sigmaconf.models import MCFSession


def _create_user(username):
    User = get_user_model()
    return User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )


@pytest.mark.django_db
def test_mcf_session_codes_are_sequential_and_report_code():
    user = _create_user("mcf_user")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Confocal proposal",
        facility_confocal=True,
    )

    session_one = MCFSession.objects.create(access_proposal=proposal, technician=user)
    session_two = MCFSession.objects.create(access_proposal=proposal, technician=user)

    pattern = re.compile(r"^MCF-(\d{2})-(\d{3})$")
    match_one = pattern.match(session_one.lot_code)
    match_two = pattern.match(session_two.lot_code)
    assert match_one
    assert match_two
    year_one, seq_one = match_one.groups()
    year_two, seq_two = match_two.groups()
    assert year_one == year_two
    assert int(seq_two) == int(seq_one) + 1
    assert session_one.report_code == f"IN-DTF-{session_one.lot_code}"


@pytest.mark.django_db
def test_mcf_session_copies_request_snapshot():
    user = _create_user("mcf_snapshot")
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Confocal snapshot",
        facility_confocal=True,
        facility_data={
            "confocal": {"confocal_sample_0_identification": "S-1"}
        },
    )

    session = MCFSession.objects.create(access_proposal=proposal, technician=user)
    assert session.request_snapshot == {"confocal_sample_0_identification": "S-1"}
