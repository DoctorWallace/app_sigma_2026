from django.urls import reverse


def test_portal_access_mode_regression(client):
    response = client.get(reverse("portal:icts_access"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "FUSION-005" in content
    assert "OLMAT" in content

    response = client.get(reverse("portal:home"))
    assert response.status_code == 200
    assert "/icts-access/" in response.content.decode("utf-8")

    response = client.get(reverse("portal:faq"))
    assert response.status_code == 200
    assert "/icts-access/" in response.content.decode("utf-8")
