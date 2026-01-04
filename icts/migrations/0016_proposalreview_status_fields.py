from django.db import migrations, models
from django.utils import timezone


def set_review_status(apps, schema_editor):
    ProposalReview = apps.get_model("icts", "ProposalReview")
    now = timezone.now()
    ProposalReview.objects.filter(decision="pending").update(status="draft")
    ProposalReview.objects.exclude(decision="pending").update(
        status="submitted",
        submitted_at=now,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("icts", "0015_accessproposal_changes_requested"),
    ]

    operations = [
        migrations.AddField(
            model_name="proposalreview",
            name="status",
            field=models.CharField(
                choices=[("draft", "Draft"), ("submitted", "Submitted")],
                db_index=True,
                default="draft",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="proposalreview",
            name="submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="proposalreview",
            name="change_request_text",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="proposalreview",
            name="change_request_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(set_review_status, reverse_code=migrations.RunPython.noop),
    ]
