import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from icts.models import AccessProposal
from icts.sigmasem.models import SEMAnalysis


def _create_user(username, groups):
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


def _create_analysis(technician, report_files):
    proposal = AccessProposal.objects.create(
        applicant=technician,
        title="SEM proposal",
        status="accepted",
        facility_sem=True,
    )
    return SEMAnalysis.objects.create(
        access_proposal=proposal,
        analysis_type="sem",
        registration_number="25-SEM-01",
        analysis_date=timezone.now().date(),
        client="X",
        technician=technician,
        report_code="IN-SEM-25-001",
        report_files=report_files,
    )


@pytest.mark.django_db
def test_sigmasem_download_scoped_file(tmp_path, client):
    technician = _create_user("sem_tech", ["tecnicos_sem_fib"])
    allowed_path = "sem_files/25-SEM-01/allowed.txt"
    report_files = [
        {
            "name": "allowed.txt",
            "path": allowed_path,
            "size": "1 KB",
            "modified": "2025-01-01 10:00",
            "type": "document",
        }
    ]

    with override_settings(MEDIA_ROOT=tmp_path):
        default_storage.save(allowed_path, ContentFile(b"ok"))
        analysis = _create_analysis(technician, report_files)

        client.force_login(technician)
        url = reverse("icts:sigmasem:download_file", args=[analysis.pk])
        response = client.get(f"{url}?path={allowed_path}")

    assert response.status_code == 200


@pytest.mark.django_db
def test_sigmasem_download_rejects_other_analysis_path(tmp_path, client):
    technician = _create_user("sem_tech_other", ["tecnicos_sem_fib"])
    allowed_path = "sem_files/25-SEM-01/allowed.txt"
    other_path = "sem_files/OTHER/secret.txt"
    report_files = [{"name": "allowed.txt", "path": allowed_path}]

    with override_settings(MEDIA_ROOT=tmp_path):
        default_storage.save(allowed_path, ContentFile(b"ok"))
        default_storage.save(other_path, ContentFile(b"secret"))
        analysis = _create_analysis(technician, report_files)

        client.force_login(technician)
        url = reverse("icts:sigmasem:download_file", args=[analysis.pk])
        response = client.get(f"{url}?path={other_path}")

    assert response.status_code == 404


@pytest.mark.django_db
def test_sigmasem_delete_rejects_other_analysis_path(tmp_path, client):
    technician = _create_user("sem_tech_delete", ["tecnicos_sem_fib"])
    allowed_path = "sem_files/25-SEM-01/allowed.txt"
    other_path = "sem_files/OTHER/secret.txt"
    report_files = [{"name": "allowed.txt", "path": allowed_path}]

    with override_settings(MEDIA_ROOT=tmp_path):
        default_storage.save(allowed_path, ContentFile(b"ok"))
        default_storage.save(other_path, ContentFile(b"secret"))
        analysis = _create_analysis(technician, report_files)

        client.force_login(technician)
        url = reverse("icts:sigmasem:delete_file", args=[analysis.pk])
        response = client.post(
            url,
            data=json.dumps({"file_path": other_path}),
            content_type="application/json",
        )

        assert response.status_code == 404
        assert default_storage.exists(other_path) is True


@pytest.mark.django_db
def test_sigmasem_blocks_path_traversal(tmp_path, client):
    technician = _create_user("sem_tech_traversal", ["tecnicos_sem_fib"])
    allowed_path = "sem_files/25-SEM-01/allowed.txt"
    report_files = [{"name": "allowed.txt", "path": allowed_path}]

    with override_settings(MEDIA_ROOT=tmp_path):
        default_storage.save(allowed_path, ContentFile(b"ok"))
        analysis = _create_analysis(technician, report_files)

        client.force_login(technician)
        download_url = reverse("icts:sigmasem:download_file", args=[analysis.pk])
        response = client.get(f"{download_url}?path=sem_files/25-SEM-01/../OTHER/secret.txt")
        assert response.status_code == 400

        delete_url = reverse("icts:sigmasem:delete_file", args=[analysis.pk])
        response = client.post(
            delete_url,
            data=json.dumps({"file_path": "../db.sqlite3"}),
            content_type="application/json",
        )
        assert response.status_code == 400


@pytest.mark.django_db
def test_sigmasem_update_report_files_rejects_injected_path(tmp_path, client):
    technician = _create_user("sem_tech_update", ["tecnicos_sem_fib"])
    allowed_path = "sem_files/25-SEM-01/allowed.txt"
    other_path = "sem_files/OTHER/secret.txt"
    report_files = [{"name": "allowed.txt", "path": allowed_path}]

    with override_settings(MEDIA_ROOT=tmp_path):
        default_storage.save(allowed_path, ContentFile(b"ok"))
        default_storage.save(other_path, ContentFile(b"secret"))
        analysis = _create_analysis(technician, report_files)

        client.force_login(technician)
        url = reverse("icts:sigmasem:update_report_files", args=[analysis.pk])
        response = client.post(
            url,
            data=json.dumps({"files": [{"name": "x", "path": other_path}]}),
            content_type="application/json",
        )

        assert response.status_code == 404
        analysis.refresh_from_db()
        assert analysis.report_files == report_files
