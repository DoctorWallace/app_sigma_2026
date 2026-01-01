import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import translation


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
@pytest.mark.parametrize("language", ["es", "en"])
def test_internal_keys_stable_in_proposal_create(client, language):
    user = _create_user(f"i18n_user_{language}", ["icts_users"])
    client.force_login(user)
    url = reverse("icts:proposal_create")

    with translation.override(language):
        response = client.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'data-tech="sem"' in html
    assert 'data-tech="confocal"' in html
    assert "sem_sample_0_identification" in html
    assert "confocal_sample_0_identification" in html
