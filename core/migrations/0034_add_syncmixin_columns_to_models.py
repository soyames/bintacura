# Generated migration to add SyncMixin columns to models without them
import uuid
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_participant_rejection_reason_and_more'),
    ]

    operations = [
        # PaymentMethod - Add SyncMixin columns
        migrations.AddField(
            model_name='paymentmethod',
            name='version',
            field=models.IntegerField(default=1, help_text='Version number for conflict detection'),
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='last_synced_at',
            field=models.DateTimeField(blank=True, help_text='When this record was last synced with cloud', null=True),
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='created_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that created this record'),
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='modified_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that last modified this record'),
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, help_text='Soft delete flag for sync purposes'),
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='deleted_at',
            field=models.DateTimeField(blank=True, help_text='When this record was marked as deleted', null=True),
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='region_code',
            field=models.CharField(db_index=True, default='global', max_length=50),
        ),
        
        # Department - Add SyncMixin columns
        migrations.AddField(
            model_name='department',
            name='version',
            field=models.IntegerField(default=1, help_text='Version number for conflict detection'),
        ),
        migrations.AddField(
            model_name='department',
            name='last_synced_at',
            field=models.DateTimeField(blank=True, help_text='When this record was last synced with cloud', null=True),
        ),
        migrations.AddField(
            model_name='department',
            name='created_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that created this record'),
        ),
        migrations.AddField(
            model_name='department',
            name='modified_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that last modified this record'),
        ),
        migrations.AddField(
            model_name='department',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, help_text='Soft delete flag for sync purposes'),
        ),
        migrations.AddField(
            model_name='department',
            name='deleted_at',
            field=models.DateTimeField(blank=True, help_text='When this record was marked as deleted', null=True),
        ),
        migrations.AddField(
            model_name='department',
            name='region_code',
            field=models.CharField(db_index=True, default='global', max_length=50),
        ),
        
        # MedicalEquipment - Add SyncMixin columns
        migrations.AddField(
            model_name='medicalequipment',
            name='version',
            field=models.IntegerField(default=1, help_text='Version number for conflict detection'),
        ),
        migrations.AddField(
            model_name='medicalequipment',
            name='last_synced_at',
            field=models.DateTimeField(blank=True, help_text='When this record was last synced with cloud', null=True),
        ),
        migrations.AddField(
            model_name='medicalequipment',
            name='created_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that created this record'),
        ),
        migrations.AddField(
            model_name='medicalequipment',
            name='modified_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that last modified this record'),
        ),
        migrations.AddField(
            model_name='medicalequipment',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, help_text='Soft delete flag for sync purposes'),
        ),
        migrations.AddField(
            model_name='medicalequipment',
            name='deleted_at',
            field=models.DateTimeField(blank=True, help_text='When this record was marked as deleted', null=True),
        ),
        migrations.AddField(
            model_name='medicalequipment',
            name='region_code',
            field=models.CharField(db_index=True, default='global', max_length=50),
        ),
    ]
