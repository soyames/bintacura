-- Fix PaymentReceipt constraints
-- Make service_transaction_id nullable since it's optional in the model

-- For DEFAULT database
ALTER TABLE payment_receipts 
ALTER COLUMN service_transaction_id DROP NOT NULL;

-- Add comment
COMMENT ON COLUMN payment_receipts.service_transaction_id IS 'Optional reference to service transaction';

-- Verify the change
SELECT 
    column_name,
    is_nullable,
    data_type
FROM information_schema.columns
WHERE table_name = 'payment_receipts' 
  AND column_name = 'service_transaction_id';
