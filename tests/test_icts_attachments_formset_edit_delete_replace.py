import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from django.urls import reverse

from icts.models import AccessProposal, Participant, ProposalAttachment


def _create_icts_user(username):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    group, _ = Group.objects.get_or_create(name="icts_users")
    user.groups.add(group)
    return user


def _base_payload(title):
    return {
        "title": title,
        "scope": "",
        "is_new_request": "on",
        "previous_access": "",
        "applicant_is_different": "",
        "organization": "",
        "contact_person": "",
        "email": "",
        "phone": "",
        "project_name": "",
        "project_type": "",
        "funding_source": "",
        "start_year": "",
        "end_year": "",
        "previous_experiments": "",
        "references": "",
        "facility_sem": "",
        "facility_sem_fib": "",
        "facility_imp": "",
        "facility_sims": "",
        "facility_confocal": "",
        "facility_vdg": "",
        "facility_profilometer": "",
        "facility_olmat": "",
        "facility_data_json": "{}",
    }


@pytest.mark.django_db
def test_edit_attachment_without_reupload_keeps_file(tmp_path, client):
    user = _create_icts_user("attach_keep")
    proposal = AccessProposal.objects.create(applicant=user, title="Draft")
    participant = Participant.objects.create(
        proposal=proposal,
        name="Solicitante Uno",
        center="Centro Uno",
        address="Direccion Uno",
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        attachment = ProposalAttachment.objects.create(
            proposal=proposal,
            name="Doc 1",
            file=SimpleUploadedFile(
                "doc.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            ),
        )

        client.force_login(user)
        response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
        prefix_participants = response.context["formset"].prefix
        prefix_attach = response.context["attachment_formset"].prefix

        data = _base_payload(proposal.title)
        data.update({
            f"{prefix_participants}-TOTAL_FORMS": "1",
            f"{prefix_participants}-INITIAL_FORMS": "1",
            f"{prefix_participants}-MIN_NUM_FORMS": "0",
            f"{prefix_participants}-MAX_NUM_FORMS": "1000",
            f"{prefix_participants}-0-id": str(participant.pk),
            f"{prefix_participants}-0-name": participant.name,
            f"{prefix_participants}-0-center": participant.center,
            f"{prefix_participants}-0-address": participant.address,
            f"{prefix_attach}-TOTAL_FORMS": "2",
            f"{prefix_attach}-INITIAL_FORMS": "1",
            f"{prefix_attach}-MIN_NUM_FORMS": "0",
            f"{prefix_attach}-MAX_NUM_FORMS": "1000",
            f"{prefix_attach}-0-id": str(attachment.pk),
            f"{prefix_attach}-0-name": attachment.name,
            f"{prefix_attach}-1-name": "",
        })

        post_response = client.post(
            reverse("icts:proposal_edit", args=[proposal.pk]),
            data,
        )

        assert post_response.status_code == 302
        assert ProposalAttachment.objects.filter(proposal=proposal).count() == 1
        attachment.refresh_from_db()
        assert attachment.file.name.endswith("doc.pdf")


@pytest.mark.django_db
def test_edit_attachment_delete_removes_file(tmp_path, client):
    user = _create_icts_user("attach_delete")
    proposal = AccessProposal.objects.create(applicant=user, title="Draft")
    participant = Participant.objects.create(
        proposal=proposal,
        name="Solicitante Uno",
        center="Centro Uno",
        address="Direccion Uno",
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        attachment = ProposalAttachment.objects.create(
            proposal=proposal,
            name="Doc 1",
            file=SimpleUploadedFile(
                "doc.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            ),
        )

        client.force_login(user)
        response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
        prefix_participants = response.context["formset"].prefix
        prefix_attach = response.context["attachment_formset"].prefix

        data = _base_payload(proposal.title)
        data.update({
            f"{prefix_participants}-TOTAL_FORMS": "1",
            f"{prefix_participants}-INITIAL_FORMS": "1",
            f"{prefix_participants}-MIN_NUM_FORMS": "0",
            f"{prefix_participants}-MAX_NUM_FORMS": "1000",
            f"{prefix_participants}-0-id": str(participant.pk),
            f"{prefix_participants}-0-name": participant.name,
            f"{prefix_participants}-0-center": participant.center,
            f"{prefix_participants}-0-address": participant.address,
            f"{prefix_attach}-TOTAL_FORMS": "2",
            f"{prefix_attach}-INITIAL_FORMS": "1",
            f"{prefix_attach}-MIN_NUM_FORMS": "0",
            f"{prefix_attach}-MAX_NUM_FORMS": "1000",
            f"{prefix_attach}-0-id": str(attachment.pk),
            f"{prefix_attach}-0-name": attachment.name,
            f"{prefix_attach}-0-DELETE": "on",
            f"{prefix_attach}-1-name": "",
        })

        post_response = client.post(
            reverse("icts:proposal_edit", args=[proposal.pk]),
            data,
        )

        assert post_response.status_code == 302
        assert ProposalAttachment.objects.filter(proposal=proposal).count() == 0


@pytest.mark.django_db
def test_edit_attachment_replace_file(tmp_path, client):
    user = _create_icts_user("attach_replace")
    proposal = AccessProposal.objects.create(applicant=user, title="Draft")
    participant = Participant.objects.create(
        proposal=proposal,
        name="Solicitante Uno",
        center="Centro Uno",
        address="Direccion Uno",
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        attachment = ProposalAttachment.objects.create(
            proposal=proposal,
            name="Doc 1",
            file=SimpleUploadedFile(
                "doc.pdf",
                b"%PDF-1.4 test",
                content_type="application/pdf",
            ),
        )

        client.force_login(user)
        response = client.get(reverse("icts:proposal_edit", args=[proposal.pk]))
        prefix_participants = response.context["formset"].prefix
        prefix_attach = response.context["attachment_formset"].prefix

        data = _base_payload(proposal.title)
        data.update({
            f"{prefix_participants}-TOTAL_FORMS": "1",
            f"{prefix_participants}-INITIAL_FORMS": "1",
            f"{prefix_participants}-MIN_NUM_FORMS": "0",
            f"{prefix_participants}-MAX_NUM_FORMS": "1000",
            f"{prefix_participants}-0-id": str(participant.pk),
            f"{prefix_participants}-0-name": participant.name,
            f"{prefix_participants}-0-center": participant.center,
            f"{prefix_participants}-0-address": participant.address,
            f"{prefix_attach}-TOTAL_FORMS": "2",
            f"{prefix_attach}-INITIAL_FORMS": "1",
            f"{prefix_attach}-MIN_NUM_FORMS": "0",
            f"{prefix_attach}-MAX_NUM_FORMS": "1000",
            f"{prefix_attach}-0-id": str(attachment.pk),
            f"{prefix_attach}-0-name": attachment.name,
            f"{prefix_attach}-1-name": "",
            f"{prefix_attach}-0-file": SimpleUploadedFile(
                "nuevo.pdf",
                b"%PDF-1.4 new",
                content_type="application/pdf",
            ),
        })

        post_response = client.post(
            reverse("icts:proposal_edit", args=[proposal.pk]),
            data,
        )

        assert post_response.status_code == 302
        attachment.refresh_from_db()
        assert ProposalAttachment.objects.filter(proposal=proposal).count() == 1
        assert "nuevo.pdf" in attachment.file.name
