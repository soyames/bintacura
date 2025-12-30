# Generated manually to fix missing SyncMixin fields on Wallet model

from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_alter_providerservice_currency_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # Add missing SyncMixin fields to core_wallets if they don't exist
                """
                DO $$
                BEGIN
                    -- Add updated_at
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='core_wallets' AND column_name='updated_at') THEN
                        ALTER TABLE core_wallets ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
                    END IF;
                    
                    -- Add version
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='core_wallets' AND column_name='version') THEN
                        ALTER TABLE core_wallets ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
                    END IF;
                    
                    -- Add last_synced_at
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='core_wallets' AND column_name='last_synced_at') THEN
                        ALTER TABLE core_wallets ADD COLUMN last_synced_at TIMESTAMP WITH TIME ZONE NULL;
                    END IF;
                    
                    -- Add created_by_instance
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='core_wallets' AND column_name='created_by_instance') THEN
                        ALTER TABLE core_wallets ADD COLUMN created_by_instance UUID NULL;
                    END IF;
                    
                    -- Add modified_by_instance
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='core_wallets' AND column_name='modified_by_instance') THEN
                        ALTER TABLE core_wallets ADD COLUMN modified_by_instance UUID NULL;
                    END IF;
                    
                    -- Add is_deleted
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='core_wallets' AND column_name='is_deleted') THEN
                        ALTER TABLE core_wallets ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
                    END IF;
                    
                    -- Add deleted_at
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='core_wallets' AND column_name='deleted_at') THEN
                        ALTER TABLE core_wallets ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE NULL;
                    END IF;
                    
                    -- Add region_code
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                  WHERE table_name='core_wallets' AND column_name='region_code') THEN
                        ALTER TABLE core_wallets ADD COLUMN region_code VARCHAR(50) NOT NULL DEFAULT 'global';
                        CREATE INDEX IF NOT EXISTS core_wallets_region_code_idx ON core_wallets(region_code);
                    END IF;
                END $$;
                """
            ],
            reverse_sql=[
                # Reverse migration - remove added columns
                """
                ALTER TABLE core_wallets DROP COLUMN IF EXISTS updated_at;
                ALTER TABLE core_wallets DROP COLUMN IF EXISTS version;
                ALTER TABLE core_wallets DROP COLUMN IF EXISTS last_synced_at;
                ALTER TABLE core_wallets DROP COLUMN IF EXISTS created_by_instance;
                ALTER TABLE core_wallets DROP COLUMN IF EXISTS modified_by_instance;
                ALTER TABLE core_wallets DROP COLUMN IF EXISTS is_deleted;
                ALTER TABLE core_wallets DROP COLUMN IF EXISTS deleted_at;
                """
            ],
        ),
    ]
