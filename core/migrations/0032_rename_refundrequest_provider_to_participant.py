# Generated migration to rename RefundRequest.provider to participant

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_add_idempotency_key'),
    ]

    operations = [
        migrations.RenameField(
            model_name='refundrequest',
            old_name='provider',
            new_name='participant',
        ),
        migrations.RenameIndex(
            model_name='refundrequest',
            new_name='refund_requests_participant_status_idx',
            old_fields=('provider', 'status'),
            new_fields=('participant', 'status'),
        ),
    ]
