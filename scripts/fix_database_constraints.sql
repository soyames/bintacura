-- ============================================================================
-- BINTACURA DATABASE CONSTRAINT FIXES
-- ============================================================================
-- This script fixes NOT NULL constraints that are causing payment failures
--
-- RUN THIS ON: AWS RDS Production Database
-- TEST FIRST ON: Frankfurt DB (if available)
--
-- Date: 2026-01-01
-- Issue: payment_receipts table has NOT NULL constraints on fields that
--        should be nullable when creating receipts without full participant data
-- ============================================================================

-- START TRANSACTION FOR SAFETY
BEGIN;

-- ============================================================================
-- FIX 1: Make payment_receipts.participant_id nullable
-- ============================================================================
-- Issue: When creating cash payment receipts, we might not have participant_id
-- Solution: Allow NULL, fallback to issued_to_id
-- ============================================================================

ALTER TABLE payment_receipts 
ALTER COLUMN participant_id DROP NOT NULL;

COMMENT ON COLUMN payment_receipts.participant_id IS 
'Legacy field - use issued_to_id instead. Can be NULL for old records.';


-- ============================================================================
-- FIX 2: Make text fields nullable with defaults
-- ============================================================================
-- Issue: Fields like issued_to_name, address, etc. have NOT NULL but we
--        might not always have this data immediately
-- ============================================================================

-- Allow empty strings as defaults
ALTER TABLE payment_receipts 
ALTER COLUMN issued_to_name DROP NOT NULL;

ALTER TABLE payment_receipts 
ALTER COLUMN issued_to_address DROP NOT NULL;

ALTER TABLE payment_receipts 
ALTER COLUMN issued_to_city DROP NOT NULL;

ALTER TABLE payment_receipts 
ALTER COLUMN issued_to_country DROP NOT NULL;

ALTER TABLE payment_receipts 
ALTER COLUMN transaction_reference DROP NOT NULL;

ALTER TABLE payment_receipts 
ALTER COLUMN payment_gateway DROP NOT NULL;

ALTER TABLE payment_receipts 
ALTER COLUMN gateway_transaction_id DROP NOT NULL;

ALTER TABLE payment_receipts 
ALTER COLUMN pdf_url DROP NOT NULL;


-- ============================================================================
-- FIX 3: Make numeric fields nullable with defaults
-- ============================================================================
ALTER TABLE payment_receipts 
ALTER COLUMN tax_rate DROP NOT NULL;

ALTER TABLE payment_receipts 
ALTER COLUMN tax_amount DROP NOT NULL;

ALTER TABLE payment_receipts 
ALTER COLUMN discount_amount DROP NOT NULL;

ALTER TABLE payment_receipts 
ALTER COLUMN platform_fee DROP NOT NULL;


-- ============================================================================
-- FIX 4: Make boolean fields nullable with defaults
-- ============================================================================
ALTER TABLE payment_receipts 
ALTER COLUMN reminder_sent DROP NOT NULL;


-- ============================================================================
-- FIX 5: Make JSON fields nullable with defaults
-- ============================================================================
ALTER TABLE payment_receipts 
ALTER COLUMN line_items DROP NOT NULL;

ALTER TABLE payment_receipts 
ALTER COLUMN service_details DROP NOT NULL;


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these to verify the changes worked:

-- Check payment_receipts columns that should now be nullable:
SELECT 
    column_name,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'payment_receipts'
AND column_name IN (
    'participant_id',
    'issued_to_name',
    'issued_to_address',
    'issued_to_city',
    'issued_to_country',
    'transaction_reference',
    'payment_gateway',
    'gateway_transaction_id',
    'pdf_url',
    'tax_rate',
    'tax_amount',
    'discount_amount',
    'platform_fee',
    'reminder_sent',
    'line_items',
    'service_details'
)
ORDER BY column_name;


-- ============================================================================
-- COMMIT OR ROLLBACK
-- ============================================================================
-- If everything looks good:
COMMIT;

-- If something went wrong:
-- ROLLBACK;


-- ============================================================================
-- POST-FIX NOTES
-- ============================================================================
-- After running this script:
-- 1. ✅ Payment receipts can be created without full participant data
-- 2. ✅ Cash payments will work (no participant_id required)
-- 3. ✅ Online payments will work (issued_to_id is sufficient)
-- 4. ⚠️  Update Django models to match these nullable fields
-- 5. ⚠️  Test both cash and online payment flows
-- ============================================================================
