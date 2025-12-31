import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.models import AccessProposal


def _create_user(username, email, group_names):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass", email=email)
    for name in group_names:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _assert_forbidden_or_redirect(response):
    assert response.status_code in (302, 403)
    if response.status_code == 302:
        assert "/accounts/login" in response.url


@pytest.mark.parametrize(
    ("url_name", "query"),
    [
        ("icts:reviewer_inbox", ""),
        ("icts:load_technique_draft", "technique=sem"),
        ("icts:load_previous_proposal", "proposal_id=1"),
    ],
)
@pytest.mark.django_db
def test_internal_views_require_login(client, url_name, query):
    url = reverse(url_name)
    if query:
        url = f"{url}?{query}"
    response = client.get(url)
    assert response.status_code == 302
    assert "/accounts/login/icts/" in response.url


@pytest.mark.django_db
def test_reviewer_inbox_allows_reviewer(client):
    reviewer = _create_user("reviewer_ok", "reviewer_ok@example.com", ["revisores"])
    client.force_login(reviewer)

    response = client.get(reverse("icts:reviewer_inbox"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_reviewer_inbox_forbids_plain_user(client):
    user = _create_user("plain_user", "plain_user@example.com", ["icts_users"])
    client.force_login(user)

    response = client.get(reverse("icts:reviewer_inbox"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_reviewer_inbox_redirects_responsable(client):
    user = _create_user(
        "responsable_reviewer",
        "responsable_reviewer@example.com",
        ["responsables", "revisores"],
    )
    client.force_login(user)

    response = client.get(reverse("icts:reviewer_inbox"))
    assert response.status_code == 302
    assert response.url == reverse("icts:responsable_dashboard")


@pytest.mark.django_db
def test_load_technique_draft_allows_plain_user(client):
    user = _create_user("draft_user", "draft_user@example.com", ["icts_users"])
    client.force_login(user)

    response = client.get(f"{reverse('icts:load_technique_draft')}?technique=sem")
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.django_db
def test_load_technique_draft_forbids_reviewer(client):
    reviewer = _create_user("draft_reviewer", "draft_reviewer@example.com", ["revisores"])
    client.force_login(reviewer)

    response = client.get(f"{reverse('icts:load_technique_draft')}?technique=sem")
    _assert_forbidden_or_redirect(response)


@pytest.mark.django_db
def test_load_previous_proposal_allows_plain_user(client):
    user = _create_user("prev_user", "prev_user@example.com", ["icts_users"])
    proposal = AccessProposal.objects.create(
        applicant=user,
        title="Prior proposal",
        status="submitted",
    )
    client.force_login(user)

    response = client.get(
        f"{reverse('icts:load_previous_proposal')}?proposal_id={proposal.pk}"
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.django_db
def test_load_previous_proposal_forbids_reviewer(client):
    reviewer = _create_user("prev_reviewer", "prev_reviewer@example.com", ["revisores"])
    client.force_login(reviewer)

    response = client.get(f"{reverse('icts:load_previous_proposal')}?proposal_id=1")
    _assert_forbidden_or_redirect(response)


@pytest.mark.parametrize(
    ("url_name", "query"),
    [
        ("icts:load_technique_draft", "technique=sem"),
        ("icts:load_previous_proposal", "proposal_id=1"),
    ],
)
@pytest.mark.django_db
def test_load_endpoints_forbid_non_icts_user(client, url_name, query):
    username = f"non_icts_{url_name.replace(':', '_')}"
    user = _create_user(username, f"{username}@example.com", [])
    client.force_login(user)

    url = reverse(url_name)
    if query:
        url = f"{url}?{query}"
    response = client.get(url)
    _assert_forbidden_or_redirect(response)
