import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.mark.django_db
def test_sigmaprofilometer_dashboard_allows_staff(client):
    User = get_user_model()
    user = User.objects.create_user(
        username="profilometer_staff",
        password="safe-pass",
        email="profilometer_staff@example.com",
        is_staff=True,
    )

    client.force_login(user)
    session = client.session
    session["module"] = "icts"
    session.save()

    response = client.get(reverse("sigmaprofilometer:dashboard"))
    assert response.status_code == 200
