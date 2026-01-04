import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
from django.urls import reverse

from icts.models import AccessProposal, Participant, ProposalAttachment


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


def _add_participant_payload(data, prefix, participant):
    data.update({
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "1",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
        f"{prefix}-0-id": str(participant.pk),
        f"{prefix}-0-name": participant.name,
        f"{prefix}-0-center": participant.center,
        f"{prefix}-0-address": participant.address,
    })


def _add_attachment_mgmt(data, formset):
    prefix = formset.prefix
    data.update({
        f"{prefix}-TOTAL_FORMS": str(formset.total_form_count()),
        f"{prefix}-INITIAL_FORMS": str(formset.initial_form_count()),
        f"{prefix}-MIN_NUM_FORMS": str(formset.min_num),
        f"{prefix}-MAX_NUM_FORMS": str(formset.max_num),
    })
    return prefix


@pytest.mark.django_db
def test_delete_existing_attachment_removes_from_db(tmp_path, client):
    user = _create_user("attach_delete_case", ["icts_users"])
    proposal = AccessProposal.objects.create(applicant=user, title="Draft")
    participant = Participant.objects.create(
        proposal=proposal,
        name="Participant One",
        center="Center One",
        address="Address One",
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
        formset_prefix = response.context["formset"].prefix
        attach_formset = response.context["attachment_formset"]
        attach_prefix = attach_formset.prefix

        data = _base_payload(proposal.title)
        _add_participant_payload(data, formset_prefix, participant)
        _add_attachment_mgmt(data, attach_formset)
        data.update({
            f"{attach_prefix}-0-id": str(attachment.pk),
            f"{attach_prefix}-0-name": attachment.name,
            f"{attach_prefix}-0-DELETE": "on",
            f"{attach_prefix}-1-name": "",
        })

        post_response = client.post(
            reverse("icts:proposal_edit", args=[proposal.pk]),
            data,
        )

        assert post_response.status_code == 302
        assert not ProposalAttachment.objects.filter(pk=attachment.pk).exists()


@pytest.mark.django_db
def test_replace_existing_attachment_keeps_single_instance(tmp_path, client):
    user = _create_user("attach_replace_case", ["icts_users"])
    proposal = AccessProposal.objects.create(applicant=user, title="Draft")
    participant = Participant.objects.create(
        proposal=proposal,
        name="Participant Two",
        center="Center Two",
        address="Address Two",
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
        formset_prefix = response.context["formset"].prefix
        attach_formset = response.context["attachment_formset"]
        attach_prefix = attach_formset.prefix

        data = _base_payload(proposal.title)
        _add_participant_payload(data, formset_prefix, participant)
        _add_attachment_mgmt(data, attach_formset)
        data.update({
            f"{attach_prefix}-0-id": str(attachment.pk),
            f"{attach_prefix}-0-name": attachment.name,
            f"{attach_prefix}-0-file": SimpleUploadedFile(
                "nuevo.pdf",
                b"%PDF-1.4 new",
                content_type="application/pdf",
            ),
            f"{attach_prefix}-1-name": "",
        })

        post_response = client.post(
            reverse("icts:proposal_edit", args=[proposal.pk]),
            data,
        )

        assert post_response.status_code == 302
        attachment.refresh_from_db()
        assert ProposalAttachment.objects.filter(proposal=proposal).count() == 1
        assert "nuevo.pdf" in attachment.file.name
