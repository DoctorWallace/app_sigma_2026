import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_login_dtf_page(client):
    response = client.get(reverse("accounts:login_dtf"))
    assert response.status_code == 200
    assert "accounts/login_dtf.html" in [t.name for t in response.templates]
