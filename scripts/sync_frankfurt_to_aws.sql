-- =============================================================================
-- DATABASE SCHEMA SYNCHRONIZATION: Frankfurt → AWS
-- Date: 2026-01-01
-- Purpose: Add missing columns from Frankfurt to AWS RDS
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. journal_entry_lines - Add SyncMixin fields
-- =============================================================================
ALTER TABLE journal_entry_lines 
ADD COLUMN IF NOT EXISTS created_by_instance UUID,
ADD COLUMN IF NOT EXISTS modified_by_instance UUID,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

COMMENT ON COLUMN journal_entry_lines.created_by_instance IS 'Instance that created this record';
COMMENT ON COLUMN journal_entry_lines.modified_by_instance IS 'Instance that last modified this record';
COMMENT ON COLUMN journal_entry_lines.deleted_at IS 'Soft delete timestamp';
COMMENT ON COLUMN journal_entry_lines.version IS 'Version number for optimistic locking';

-- =============================================================================
-- 2. operating_rooms - Add SyncMixin fields
-- =============================================================================
ALTER TABLE operating_rooms 
ADD COLUMN IF NOT EXISTS created_by_instance UUID,
ADD COLUMN IF NOT EXISTS modified_by_instance UUID,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

COMMENT ON COLUMN operating_rooms.created_by_instance IS 'Instance that created this record';
COMMENT ON COLUMN operating_rooms.modified_by_instance IS 'Instance that last modified this record';
COMMENT ON COLUMN operating_rooms.deleted_at IS 'Soft delete timestamp';
COMMENT ON COLUMN operating_rooms.version IS 'Version number for optimistic locking';

-- =============================================================================
-- 3. projects - Add SyncMixin fields
-- =============================================================================
ALTER TABLE projects 
ADD COLUMN IF NOT EXISTS created_by_instance UUID,
ADD COLUMN IF NOT EXISTS modified_by_instance UUID,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

COMMENT ON COLUMN projects.created_by_instance IS 'Instance that created this record';
COMMENT ON COLUMN projects.modified_by_instance IS 'Instance that last modified this record';
COMMENT ON COLUMN projects.deleted_at IS 'Soft delete timestamp';
COMMENT ON COLUMN projects.version IS 'Version number for optimistic locking';

-- =============================================================================
-- 4. surgery_schedules - Add comprehensive medical fields
-- =============================================================================
ALTER TABLE surgery_schedules
ADD COLUMN IF NOT EXISTS actual_duration_minutes INTEGER,
ADD COLUMN IF NOT EXISTS assistant_surgeon_id UUID,
ADD COLUMN IF NOT EXISTS cancellation_reason TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS circulating_nurse_id UUID,
ADD COLUMN IF NOT EXISTS consent_signed BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS created_by_instance UUID,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS estimated_blood_loss_ml INTEGER,
ADD COLUMN IF NOT EXISTS implants_needed TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS modified_by_instance UUID,
ADD COLUMN IF NOT EXISTS post_op_destination VARCHAR(100) DEFAULT '',
ADD COLUMN IF NOT EXISTS post_op_orders TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS pre_op_checklist_complete BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS scrub_nurse_id UUID,
ADD COLUMN IF NOT EXISTS special_equipment TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS surgical_site_marked BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

-- Add foreign key constraints
ALTER TABLE surgery_schedules
ADD CONSTRAINT fk_surgery_assistant_surgeon 
    FOREIGN KEY (assistant_surgeon_id) REFERENCES participants(uid) ON DELETE SET NULL,
ADD CONSTRAINT fk_surgery_circulating_nurse 
    FOREIGN KEY (circulating_nurse_id) REFERENCES participants(uid) ON DELETE SET NULL,
ADD CONSTRAINT fk_surgery_scrub_nurse 
    FOREIGN KEY (scrub_nurse_id) REFERENCES participants(uid) ON DELETE SET NULL;

COMMENT ON COLUMN surgery_schedules.actual_duration_minutes IS 'Actual surgery duration in minutes';
COMMENT ON COLUMN surgery_schedules.assistant_surgeon_id IS 'Assistant surgeon participant UID';
COMMENT ON COLUMN surgery_schedules.cancellation_reason IS 'Reason if surgery was cancelled';
COMMENT ON COLUMN surgery_schedules.consent_signed IS 'Patient consent signed';
COMMENT ON COLUMN surgery_schedules.estimated_blood_loss_ml IS 'Estimated blood loss in milliliters';
COMMENT ON COLUMN surgery_schedules.pre_op_checklist_complete IS 'Pre-operative checklist completed';
COMMENT ON COLUMN surgery_schedules.surgical_site_marked IS 'Surgical site properly marked';

-- =============================================================================
-- 5. transaction_fees - Complete schema replacement
-- =============================================================================

-- Backup existing data if any
CREATE TABLE IF NOT EXISTS transaction_fees_backup AS 
SELECT * FROM transaction_fees WHERE 1=0;

-- Drop existing columns (AWS schema)
ALTER TABLE transaction_fees
DROP COLUMN IF EXISTS fee_amount CASCADE,
DROP COLUMN IF EXISTS fee_percentage CASCADE,
DROP COLUMN IF EXISTS fee_type CASCADE,
DROP COLUMN IF EXISTS sync_status CASCADE,
DROP COLUMN IF EXISTS sync_version CASCADE;

-- Add Frankfurt schema columns
ALTER TABLE transaction_fees
ADD COLUMN IF NOT EXISTS collected_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS created_by_instance UUID,
ADD COLUMN IF NOT EXISTS currency_code VARCHAR(3) NOT NULL DEFAULT 'XOF',
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS exchange_rate_used NUMERIC(20, 10) NOT NULL DEFAULT 1.0,
ADD COLUMN IF NOT EXISTS fee_collected BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS gross_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS gross_amount_local NUMERIC(12, 2),
ADD COLUMN IF NOT EXISTS gross_amount_usd NUMERIC(12, 2),
ADD COLUMN IF NOT EXISTS modified_by_instance UUID,
ADD COLUMN IF NOT EXISTS net_amount_to_provider NUMERIC(12, 2) NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS platform_fee_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS platform_fee_amount_local NUMERIC(12, 2),
ADD COLUMN IF NOT EXISTS platform_fee_amount_usd NUMERIC(12, 2),
ADD COLUMN IF NOT EXISTS platform_fee_rate NUMERIC(5, 4) NOT NULL DEFAULT 0.01,
ADD COLUMN IF NOT EXISTS tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS tax_amount_local NUMERIC(12, 2),
ADD COLUMN IF NOT EXISTS tax_amount_usd NUMERIC(12, 2),
ADD COLUMN IF NOT EXISTS tax_rate NUMERIC(5, 4) NOT NULL DEFAULT 0.18,
ADD COLUMN IF NOT EXISTS total_fee_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

-- Create index on currency_code
CREATE INDEX IF NOT EXISTS idx_transaction_fees_currency ON transaction_fees(currency_code);
CREATE INDEX IF NOT EXISTS idx_transaction_fees_collected ON transaction_fees(fee_collected);

COMMENT ON COLUMN transaction_fees.currency_code IS 'ISO 4217 currency code';
COMMENT ON COLUMN transaction_fees.exchange_rate_used IS 'Exchange rate used for conversion';
COMMENT ON COLUMN transaction_fees.fee_collected IS 'Whether platform fee has been collected';
COMMENT ON COLUMN transaction_fees.platform_fee_rate IS 'Platform fee rate (e.g., 0.01 = 1%)';
COMMENT ON COLUMN transaction_fees.tax_rate IS 'Tax rate (e.g., 0.18 = 18%)';

-- =============================================================================
-- COMMIT
-- =============================================================================

COMMIT;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Verify journal_entry_lines
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'journal_entry_lines' 
  AND column_name IN ('created_by_instance', 'modified_by_instance', 'deleted_at', 'version')
ORDER BY column_name;

-- Verify operating_rooms
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'operating_rooms' 
  AND column_name IN ('created_by_instance', 'modified_by_instance', 'deleted_at', 'version')
ORDER BY column_name;

-- Verify projects
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'projects' 
  AND column_name IN ('created_by_instance', 'modified_by_instance', 'deleted_at', 'version')
ORDER BY column_name;

-- Verify surgery_schedules
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'surgery_schedules' 
  AND column_name IN ('actual_duration_minutes', 'assistant_surgeon_id', 'consent_signed', 'pre_op_checklist_complete')
ORDER BY column_name;

-- Verify transaction_fees
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'transaction_fees' 
  AND column_name IN ('currency_code', 'platform_fee_rate', 'tax_rate', 'gross_amount')
ORDER BY column_name;
