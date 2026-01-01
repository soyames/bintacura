-- ================================================================
-- AWS Database Column Sync Script
-- Adds missing columns from Frankfurt to AWS Default Database
-- Date: 2026-01-01
-- ================================================================

-- WARNING: This script modifies database schema
-- TEST in development before running in production
-- BACKUP database before running

BEGIN;

-- ================================================================
-- 1. Add SyncMixin fields to tables missing them
-- ================================================================

-- journal_entry_lines
ALTER TABLE journal_entry_lines 
ADD COLUMN IF NOT EXISTS created_by_instance UUID NULL,
ADD COLUMN IF NOT EXISTS modified_by_instance UUID NULL,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE NULL,
ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

-- operating_rooms
ALTER TABLE operating_rooms 
ADD COLUMN IF NOT EXISTS created_by_instance UUID NULL,
ADD COLUMN IF NOT EXISTS modified_by_instance UUID NULL,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE NULL,
ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

-- projects
ALTER TABLE projects 
ADD COLUMN IF NOT EXISTS created_by_instance UUID NULL,
ADD COLUMN IF NOT EXISTS modified_by_instance UUID NULL,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE NULL,
ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

-- ================================================================
-- 2. Add detailed surgery_schedules fields
-- ================================================================

ALTER TABLE surgery_schedules
ADD COLUMN IF NOT EXISTS actual_duration_minutes INTEGER NULL,
ADD COLUMN IF NOT EXISTS assistant_surgeon_id UUID NULL,
ADD COLUMN IF NOT EXISTS cancellation_reason TEXT NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS circulating_nurse_id UUID NULL,
ADD COLUMN IF NOT EXISTS consent_signed BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS created_by_instance UUID NULL,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE NULL,
ADD COLUMN IF NOT EXISTS estimated_blood_loss_ml INTEGER NULL,
ADD COLUMN IF NOT EXISTS implants_needed TEXT NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS modified_by_instance UUID NULL,
ADD COLUMN IF NOT EXISTS post_op_destination VARCHAR(255) NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS post_op_orders TEXT NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS pre_op_checklist_complete BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS scrub_nurse_id UUID NULL,
ADD COLUMN IF NOT EXISTS special_equipment TEXT NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS surgical_site_marked BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

-- ================================================================
-- 3. Add detailed transaction_fees fields
-- ================================================================

ALTER TABLE transaction_fees
ADD COLUMN IF NOT EXISTS collected_at TIMESTAMP WITH TIME ZONE NULL,
ADD COLUMN IF NOT EXISTS created_by_instance UUID NULL,
ADD COLUMN IF NOT EXISTS currency_code VARCHAR(10) NOT NULL DEFAULT 'XOF',
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE NULL,
ADD COLUMN IF NOT EXISTS exchange_rate_used NUMERIC(10, 6) NOT NULL DEFAULT 1.0,
ADD COLUMN IF NOT EXISTS fee_collected BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS gross_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS gross_amount_local NUMERIC(10, 2) NULL,
ADD COLUMN IF NOT EXISTS gross_amount_usd NUMERIC(10, 2) NULL,
ADD COLUMN IF NOT EXISTS modified_by_instance UUID NULL,
ADD COLUMN IF NOT EXISTS net_amount_to_provider NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS platform_fee_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS platform_fee_amount_local NUMERIC(10, 2) NULL,
ADD COLUMN IF NOT EXISTS platform_fee_amount_usd NUMERIC(10, 2) NULL,
ADD COLUMN IF NOT EXISTS platform_fee_rate NUMERIC(5, 4) NOT NULL DEFAULT 0.01,
ADD COLUMN IF NOT EXISTS tax_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS tax_amount_local NUMERIC(10, 2) NULL,
ADD COLUMN IF NOT EXISTS tax_amount_usd NUMERIC(10, 2) NULL,
ADD COLUMN IF NOT EXISTS tax_rate NUMERIC(5, 4) NOT NULL DEFAULT 0.18,
ADD COLUMN IF NOT EXISTS total_fee_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

-- ================================================================
-- 4. Create indexes for foreign keys
-- ================================================================

CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_created_by ON journal_entry_lines(created_by_instance);
CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_modified_by ON journal_entry_lines(modified_by_instance);

CREATE INDEX IF NOT EXISTS idx_operating_rooms_created_by ON operating_rooms(created_by_instance);
CREATE INDEX IF NOT EXISTS idx_operating_rooms_modified_by ON operating_rooms(modified_by_instance);

CREATE INDEX IF NOT EXISTS idx_projects_created_by ON projects(created_by_instance);
CREATE INDEX IF NOT EXISTS idx_projects_modified_by ON projects(modified_by_instance);

CREATE INDEX IF NOT EXISTS idx_surgery_schedules_assistant_surgeon ON surgery_schedules(assistant_surgeon_id);
CREATE INDEX IF NOT EXISTS idx_surgery_schedules_circulating_nurse ON surgery_schedules(circulating_nurse_id);
CREATE INDEX IF NOT EXISTS idx_surgery_schedules_scrub_nurse ON surgery_schedules(scrub_nurse_id);
CREATE INDEX IF NOT EXISTS idx_surgery_schedules_created_by ON surgery_schedules(created_by_instance);
CREATE INDEX IF NOT EXISTS idx_surgery_schedules_modified_by ON surgery_schedules(modified_by_instance);

CREATE INDEX IF NOT EXISTS idx_transaction_fees_created_by ON transaction_fees(created_by_instance);
CREATE INDEX IF NOT EXISTS idx_transaction_fees_modified_by ON transaction_fees(modified_by_instance);

-- ================================================================
-- 5. Add comments to document the columns
-- ================================================================

COMMENT ON COLUMN journal_entry_lines.version IS 'Sync version for offline conflict resolution';
COMMENT ON COLUMN operating_rooms.version IS 'Sync version for offline conflict resolution';
COMMENT ON COLUMN projects.version IS 'Sync version for offline conflict resolution';
COMMENT ON COLUMN surgery_schedules.version IS 'Sync version for offline conflict resolution';
COMMENT ON COLUMN transaction_fees.version IS 'Sync version for offline conflict resolution';

COMMIT;

-- ================================================================
-- Verification Queries
-- ================================================================

-- Run these to verify the changes
/*
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'journal_entry_lines'
ORDER BY ordinal_position;

SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'surgery_schedules'
ORDER BY ordinal_position;

SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'transaction_fees'
ORDER BY ordinal_position;
*/
