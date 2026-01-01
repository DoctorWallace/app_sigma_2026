import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal


def _create_user(username: str, groups):
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


@pytest.mark.django_db
def test_get_proposal_samples_requires_login(client):
    applicant = _create_user("anon_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Accepted SEM",
        status="accepted",
        facility_sem=True,
    )

    url = reverse("icts:sigmasem:get_proposal_samples", args=[proposal.pk])
    response = client.get(url)

    assert response.status_code == 302
    assert "/accounts/login/icts/" in response["Location"]


@pytest.mark.django_db
def test_get_proposal_samples_blocks_non_sem_user(client):
    applicant = _create_user("plain_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Accepted SEM",
        status="accepted",
        facility_sem=True,
    )
    user = _create_user("plain_user", ["icts_users"])

    client.force_login(user)
    url = reverse("icts:sigmasem:get_proposal_samples", args=[proposal.pk])
    response = client.get(url)

    assert response.status_code in {302, 403}


@pytest.mark.django_db
def test_get_proposal_samples_requires_accepted_sem_proposal(client):
    applicant = _create_user("sem_applicant", ["icts_users"])
    proposal_ok = AccessProposal.objects.create(
        applicant=applicant,
        title="Accepted SEM",
        status="accepted",
        facility_sem=True,
        facility_data={
            "sem": {
                "sem_sample_0_identification": "SEM-001",
                "sem_sample_0_name": "Sample A",
            }
        },
    )
    proposal_draft = AccessProposal.objects.create(
        applicant=applicant,
        title="Draft SEM",
        status="draft",
        facility_sem=True,
    )
    proposal_non_sem = AccessProposal.objects.create(
        applicant=applicant,
        title="Accepted non-SEM",
        status="accepted",
        facility_sem=False,
        facility_sem_fib=False,
    )
    tech = _create_user("sem_tech", ["tecnicos_sem_fib"])

    client.force_login(tech)

    ok_url = reverse("icts:sigmasem:get_proposal_samples", args=[proposal_ok.pk])
    response_ok = client.get(ok_url)
    assert response_ok.status_code == 200

    draft_url = reverse("icts:sigmasem:get_proposal_samples", args=[proposal_draft.pk])
    response_draft = client.get(draft_url)
    assert response_draft.status_code == 404

    non_sem_url = reverse("icts:sigmasem:get_proposal_samples", args=[proposal_non_sem.pk])
    response_non_sem = client.get(non_sem_url)
    assert response_non_sem.status_code == 404
