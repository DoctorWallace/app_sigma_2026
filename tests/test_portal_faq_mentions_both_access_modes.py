from django.urls import reverse


def test_portal_faq_mentions_access_modes(client):
    response = client.get(reverse("portal:faq"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Acceso competitivo" in content
    assert "Solicitud directa" in content
