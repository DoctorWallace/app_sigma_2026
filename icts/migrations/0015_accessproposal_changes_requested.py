from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("icts", "0014_alter_accessproposal_access_code_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="accessproposal",
            name="responsable_comment",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="accessproposal",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("submitted", "Submitted"),
                    ("changes_requested", "Changes requested"),
                    ("accepted", "Accepted"),
                    ("rejected", "Rejected"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
    ]
