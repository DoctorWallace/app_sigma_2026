from django.urls import reverse
from django.utils import translation


def test_icts_access_page_renders_content(client):
    response = client.get(reverse("portal:icts_access"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert ("Acceso competitivo" in content) or ("Competitive access" in content)
    assert ("Solicitud directa" in content) or ("Direct request" in content)


def test_icts_access_page_includes_tariffs(client):
    response = client.get(reverse("portal:icts_access"))
    content = response.content.decode("utf-8")
    assert "FUSION-005" in content
    assert "92,36" in content
    assert "OLMAT" in content
    assert ("Por definir" in content) or ("To be defined" in content)
