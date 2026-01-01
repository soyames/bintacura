# Generated manually to rename provider_id to participant_id in participant_services table

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_add_syncmixin_columns_to_models'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Rename provider_id column to participant_id if it exists
            DO $$ 
            BEGIN
                IF EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'participant_services' 
                    AND column_name = 'provider_id'
                ) THEN
                    ALTER TABLE participant_services 
                    RENAME COLUMN provider_id TO participant_id;
                END IF;
            END $$;
            """,
            reverse_sql="""
            -- Rename back to provider_id
            DO $$ 
            BEGIN
                IF EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name = 'participant_services' 
                    AND column_name = 'participant_id'
                ) THEN
                    ALTER TABLE participant_services 
                    RENAME COLUMN participant_id TO provider_id;
                END IF;
            END $$;
            """
        ),
    ]
