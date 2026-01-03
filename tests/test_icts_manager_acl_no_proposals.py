import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal


def _create_user(username, groups):
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
def test_manager_cannot_access_proposal_detail(client):
    manager = _create_user("manager_acl", ["managers"])
    applicant = _create_user("applicant_acl", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Secret proposal",
        facility_sem=True,
    )

    client.force_login(manager)
    response = client.get(reverse("icts:proposal_detail", args=[proposal.pk]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_cannot_access_reviewer_inbox(client):
    manager = _create_user("manager_inbox", ["managers"])

    client.force_login(manager)
    response = client.get(reverse("icts:reviewer_inbox"))

    assert response.status_code == 302
    assert response.url == reverse("icts:manager_dashboard")


@pytest.mark.django_db
def test_manager_cannot_access_olmat_dashboard(client):
    manager = _create_user("manager_olmat", ["managers"])

    client.force_login(manager)
    response = client.get(reverse("icts:olmat_dashboard"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_dashboard_excludes_pii(client):
    manager = _create_user("manager_dash", ["managers"])
    applicant = _create_user("pii_applicant", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=applicant,
        title="Private proposal",
        facility_sem=True,
    )

    client.force_login(manager)
    response = client.get(reverse("icts:manager_dashboard"))

    assert response.status_code == 200
    content = response.content.decode("utf-8", errors="ignore")
    assert applicant.username not in content
    assert applicant.email not in content
    assert proposal.title not in content
