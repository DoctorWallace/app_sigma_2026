from django.db import migrations, models
from django.utils import timezone


def backfill_review_draft_state(apps, schema_editor):
    ProposalReview = apps.get_model("icts", "ProposalReview")
    now = timezone.now()
    updates = []
    for review in ProposalReview.objects.all():
        has_data = (
            review.decision != "pending"
            or review.feasibility_ok is not None
            or review.score_scientific_quality is not None
            or review.score_need_infrastructure is not None
            or review.score_industrial_potential is not None
            or bool((review.comments or "").strip())
        )
        review.status = "draft"
        review.submitted_at = None
        if has_data and review.draft_saved_at is None:
            review.draft_saved_at = now
        updates.append(review)
    if updates:
        ProposalReview.objects.bulk_update(
            updates, ["status", "submitted_at", "draft_saved_at"]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("icts", "0016_proposalreview_status_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="proposalreview",
            name="draft_saved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="proposalreview",
            name="reopened_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            backfill_review_draft_state, reverse_code=migrations.RunPython.noop
        ),
    ]
