# Manual migration to sync ParticipantService model state with actual database
# Generated manually on 2026-01-01
# 
# Background: The database already has all required fields including:
# - id (bigint primary key)
# - uid (uuid, NOT NULL, UNIQUE, default: gen_random_uuid())
# - metadata (jsonb)
# - All SyncMixin fields (version, last_synced_at, created_by_instance, modified_by_instance, is_deleted, deleted_at)
# 
# This migration updates Django's state to match without altering the database.

from django.db import migrations, models
import uuid
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_fix_participantservice_state'),
    ]

    operations = [
        # Mark model state as matching database - no actual SQL operations
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='participantservice',
                    name='id',
                    field=models.BigAutoField(primary_key=True),
                ),
                migrations.AlterField(
                    model_name='participantservice',
                    name='uid',
                    field=models.UUIDField(editable=False, unique=True, db_index=True),
                ),
                migrations.AlterField(
                    model_name='participantservice',
                    name='participant',
                    field=models.ForeignKey(
                        blank=True, 
                        db_column='participant_id', 
                        null=True, 
                        on_delete=django.db.models.deletion.CASCADE, 
                        related_name='services', 
                        to=settings.AUTH_USER_MODEL
                    ),
                ),
                migrations.AlterField(
                    model_name='participantservice',
                    name='metadata',
                    field=models.JSONField(default=dict, blank=True, null=True),
                ),
                migrations.AlterField(
                    model_name='participantservice',
                    name='version',
                    field=models.IntegerField(),
                ),
                migrations.AlterField(
                    model_name='participantservice',
                    name='created_by_instance',
                    field=models.UUIDField(),
                ),
                migrations.AlterField(
                    model_name='participantservice',
                    name='modified_by_instance',
                    field=models.UUIDField(),
                ),
                migrations.AlterField(
                    model_name='participantservice',
                    name='is_deleted',
                    field=models.BooleanField(),
                ),
            ]
        ),
    ]
