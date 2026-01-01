import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from portal.models import DirectServiceRequest


@pytest.mark.django_db
def test_direct_request_submission_creates_record(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    pdf_file = SimpleUploadedFile(
        "formulario.pdf",
        b"%PDF-1.4\n%dummy\n%%EOF\n",
        content_type="application/pdf",
    )
    response = client.post(
        reverse("portal:direct_request_create"),
        data={
            "full_name": "Ana Laboratorio",
            "email": "ana@example.com",
            "requested_service": "SEM",
            "consent": "on",
            "is_digitally_signed": "on",
            "form_pdf": pdf_file,
        },
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("portal:direct_request_success")
    obj = DirectServiceRequest.objects.get()
    assert obj.status == "received"


@pytest.mark.django_db
def test_direct_request_submission_requires_consent(client):
    response = client.post(
        reverse("portal:direct_request_create"),
        data={
            "full_name": "Ana Laboratorio",
            "email": "ana@example.com",
            "requested_service": "SEM",
        },
    )
    assert response.status_code == 200
    assert DirectServiceRequest.objects.count() == 0
    assert "Debes aceptar el consentimiento" in response.content.decode("utf-8")
