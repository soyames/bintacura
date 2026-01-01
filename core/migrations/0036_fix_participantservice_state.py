# Manual migration to fix ParticipantService state to match actual database schema
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0035_rename_provider_id_to_participant_id'),
    ]

    operations = [
        # This migration intentionally has no operations
        # It's just to mark that ParticipantService model state is correct as-is
        # The database already has the correct schema with:
        # - uid (already exists in DB)
        # - metadata (already exists in DB)
        # - NO SyncMixin fields (they don't exist in DB)
    ]
