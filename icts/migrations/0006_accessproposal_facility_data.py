from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('icts', '0005_backfill_user_siglas'),
    ]

    operations = [
        migrations.AddField(
            model_name='accessproposal',
            name='facility_data',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]

