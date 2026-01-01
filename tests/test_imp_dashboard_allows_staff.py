import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse


@pytest.mark.django_db
def test_imp_dashboard_allows_staff(client):
    User = get_user_model()
    user = User.objects.create_user(
        username="imp_staff",
        password="safe-pass",
        email="imp_staff@example.com",
        is_staff=True,
    )

    client.force_login(user)
    session = client.session
    session["module"] = "icts"
    session.save()

    response = client.get(reverse("sigmaimp:imp_dashboard"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_imp_dashboard_denies_non_tech(client):
    User = get_user_model()
    user = User.objects.create_user(
        username="imp_plain",
        password="safe-pass",
        email="imp_plain@example.com",
    )
    group, _ = Group.objects.get_or_create(name="icts_users")
    user.groups.add(group)

    client.force_login(user)
    session = client.session
    session["module"] = "icts"
    session.save()

    response = client.get(reverse("sigmaimp:imp_dashboard"))
    assert response.status_code in {302, 403}
