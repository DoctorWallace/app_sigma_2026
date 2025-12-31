import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_portal_home_ok(client):
    response = client.get(reverse("portal:home"))
    assert response.status_code == 200
    assert "portal/home.html" in [t.name for t in response.templates]
