# Generated migration to add SyncMixin columns
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0015_alter_cashregister_created_by_instance_and_more'),
    ]

    operations = [
                # PharmacyCounter - Add SyncMixin columns
        migrations.AddField(
            model_name='pharmacycounter',
            name='version',
            field=models.IntegerField(default=1, help_text='Version number for conflict detection'),
        ),
        migrations.AddField(
            model_name='pharmacycounter',
            name='last_synced_at',
            field=models.DateTimeField(blank=True, help_text='When this record was last synced with cloud', null=True),
        ),
        migrations.AddField(
            model_name='pharmacycounter',
            name='created_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that created this record'),
        ),
        migrations.AddField(
            model_name='pharmacycounter',
            name='modified_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that last modified this record'),
        ),
        migrations.AddField(
            model_name='pharmacycounter',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, help_text='Soft delete flag for sync purposes'),
        ),
        migrations.AddField(
            model_name='pharmacycounter',
            name='deleted_at',
            field=models.DateTimeField(blank=True, help_text='When this record was marked as deleted', null=True),
        ),
        migrations.AddField(
            model_name='pharmacycounter',
            name='region_code',
            field=models.CharField(db_index=True, default='global', max_length=50),
        ),
                # PharmacyService - Add SyncMixin columns
        migrations.AddField(
            model_name='pharmacyservice',
            name='version',
            field=models.IntegerField(default=1, help_text='Version number for conflict detection'),
        ),
        migrations.AddField(
            model_name='pharmacyservice',
            name='last_synced_at',
            field=models.DateTimeField(blank=True, help_text='When this record was last synced with cloud', null=True),
        ),
        migrations.AddField(
            model_name='pharmacyservice',
            name='created_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that created this record'),
        ),
        migrations.AddField(
            model_name='pharmacyservice',
            name='modified_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that last modified this record'),
        ),
        migrations.AddField(
            model_name='pharmacyservice',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, help_text='Soft delete flag for sync purposes'),
        ),
        migrations.AddField(
            model_name='pharmacyservice',
            name='deleted_at',
            field=models.DateTimeField(blank=True, help_text='When this record was marked as deleted', null=True),
        ),
        migrations.AddField(
            model_name='pharmacyservice',
            name='region_code',
            field=models.CharField(db_index=True, default='global', max_length=50),
        ),
                # PharmacyStaff - Add SyncMixin columns
        migrations.AddField(
            model_name='pharmacystaff',
            name='version',
            field=models.IntegerField(default=1, help_text='Version number for conflict detection'),
        ),
        migrations.AddField(
            model_name='pharmacystaff',
            name='last_synced_at',
            field=models.DateTimeField(blank=True, help_text='When this record was last synced with cloud', null=True),
        ),
        migrations.AddField(
            model_name='pharmacystaff',
            name='created_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that created this record'),
        ),
        migrations.AddField(
            model_name='pharmacystaff',
            name='modified_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that last modified this record'),
        ),
        migrations.AddField(
            model_name='pharmacystaff',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, help_text='Soft delete flag for sync purposes'),
        ),
        migrations.AddField(
            model_name='pharmacystaff',
            name='deleted_at',
            field=models.DateTimeField(blank=True, help_text='When this record was marked as deleted', null=True),
        ),
        migrations.AddField(
            model_name='pharmacystaff',
            name='region_code',
            field=models.CharField(db_index=True, default='global', max_length=50),
        ),
                # PharmacyInventory - Add SyncMixin columns
        migrations.AddField(
            model_name='pharmacyinventory',
            name='version',
            field=models.IntegerField(default=1, help_text='Version number for conflict detection'),
        ),
        migrations.AddField(
            model_name='pharmacyinventory',
            name='last_synced_at',
            field=models.DateTimeField(blank=True, help_text='When this record was last synced with cloud', null=True),
        ),
        migrations.AddField(
            model_name='pharmacyinventory',
            name='created_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that created this record'),
        ),
        migrations.AddField(
            model_name='pharmacyinventory',
            name='modified_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that last modified this record'),
        ),
        migrations.AddField(
            model_name='pharmacyinventory',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, help_text='Soft delete flag for sync purposes'),
        ),
        migrations.AddField(
            model_name='pharmacyinventory',
            name='deleted_at',
            field=models.DateTimeField(blank=True, help_text='When this record was marked as deleted', null=True),
        ),
        migrations.AddField(
            model_name='pharmacyinventory',
            name='region_code',
            field=models.CharField(db_index=True, default='global', max_length=50),
        ),
                # PharmacySupplier - Add SyncMixin columns
        migrations.AddField(
            model_name='pharmacysupplier',
            name='version',
            field=models.IntegerField(default=1, help_text='Version number for conflict detection'),
        ),
        migrations.AddField(
            model_name='pharmacysupplier',
            name='last_synced_at',
            field=models.DateTimeField(blank=True, help_text='When this record was last synced with cloud', null=True),
        ),
        migrations.AddField(
            model_name='pharmacysupplier',
            name='created_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that created this record'),
        ),
        migrations.AddField(
            model_name='pharmacysupplier',
            name='modified_by_instance',
            field=models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that last modified this record'),
        ),
        migrations.AddField(
            model_name='pharmacysupplier',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, help_text='Soft delete flag for sync purposes'),
        ),
        migrations.AddField(
            model_name='pharmacysupplier',
            name='deleted_at',
            field=models.DateTimeField(blank=True, help_text='When this record was marked as deleted', null=True),
        ),
        migrations.AddField(
            model_name='pharmacysupplier',
            name='region_code',
            field=models.CharField(db_index=True, default='global', max_length=50),
        ),
    ]