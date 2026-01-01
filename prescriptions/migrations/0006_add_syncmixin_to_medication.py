# Generated migration to add SyncMixin columns
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prescriptions', '0005_alter_fulfillmentitem_created_by_instance_and_more'),
    ]

    operations = [
                # Medication - Add SyncMixin columns
        migrations.AddField(
            model_name='medication',
            name='version',
            field=models.IntegerField(default=1, help_text='Version number for conflict detection'),
        ),
        migrations.AddField(
            model_name='medication',
            name='last_synced_at',
            field=models.DateTimeField(blank=True, help_text='When this record was last synced with cloud', null=True),
        ),
        migrations.AddField(
            model_name='medication',
            name='created_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that created this record'),
        ),
        migrations.AddField(
            model_name='medication',
            name='modified_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that last modified this record'),
        ),
        migrations.AddField(
            model_name='medication',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, help_text='Soft delete flag for sync purposes'),
        ),
        migrations.AddField(
            model_name='medication',
            name='deleted_at',
            field=models.DateTimeField(blank=True, help_text='When this record was marked as deleted', null=True),
        ),
        migrations.AddField(
            model_name='medication',
            name='region_code',
            field=models.CharField(db_index=True, default='global', max_length=50),
        ),
    ]