# Generated manually to fix missing participant_services table

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_alter_systemconfiguration_default_consultation_currency_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS participant_services (
                id UUID PRIMARY KEY,
                provider_id UUID NOT NULL REFERENCES participants(uid) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(50) NOT NULL,
                description TEXT NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                currency VARCHAR(3) NOT NULL DEFAULT 'XOF',
                duration_minutes INTEGER,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                is_available BOOLEAN NOT NULL DEFAULT TRUE,
                region_code VARCHAR(50) NOT NULL DEFAULT 'global',
                updated_at TIMESTAMP,
                version INTEGER DEFAULT 1,
                last_synced_at TIMESTAMP,
                created_by_instance VARCHAR(100),
                modified_by_instance VARCHAR(100),
                is_deleted BOOLEAN DEFAULT FALSE,
                deleted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS participant_provide_86309b_idx 
                ON participant_services (provider_id, category);
            CREATE INDEX IF NOT EXISTS participant_is_acti_d65640_idx 
                ON participant_services (is_active, is_available);
            CREATE INDEX IF NOT EXISTS participant_region_idx 
                ON participant_services (region_code);
            """,
            reverse_sql="DROP TABLE IF EXISTS participant_services CASCADE;"
        ),
    ]
