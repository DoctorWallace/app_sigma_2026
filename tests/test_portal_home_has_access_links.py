from django.urls import reverse


def test_portal_home_links_to_icts_access(client):
    response = client.get(reverse("portal:home"))
    assert response.status_code == 200
    assert "/icts-access/" in response.content.decode("utf-8")
