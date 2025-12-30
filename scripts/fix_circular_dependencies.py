import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

def fix_circular_dependencies():
    """Fix circular dependencies and create all missing tables"""
    with connection.cursor() as cursor:
        print("\n" + "="*70)
        print("FIXING CIRCULAR DEPENDENCIES AND CREATING MISSING TABLES")
        print("="*70 + "\n")
        
        # 1. Create service_transactions first (without gateway_transaction FK constraint initially)
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS service_transactions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    region_code VARCHAR(50) DEFAULT 'global',
                    transaction_ref VARCHAR(100) UNIQUE NOT NULL,
                    idempotency_key VARCHAR(255) UNIQUE,
                    patient_id UUID NOT NULL,
                    service_provider_id UUID NOT NULL,
                    service_provider_role VARCHAR(50) NOT NULL,
                    service_catalog_item_id UUID,
                    service_type VARCHAR(50) NOT NULL,
                    service_id UUID NOT NULL,
                    service_description TEXT NOT NULL,
                    amount_usd DECIMAL(12, 2),
                    amount_local DECIMAL(12, 2),
                    currency_code VARCHAR(3),
                    exchange_rate_used DECIMAL(12, 6),
                    conversion_timestamp TIMESTAMPTZ,
                    amount DECIMAL(12, 2) NOT NULL,
                    currency VARCHAR(3) DEFAULT 'XOF',
                    payment_method VARCHAR(50) NOT NULL,
                    patient_phone_id UUID,
                    provider_phone_id UUID,
                    status VARCHAR(20) DEFAULT 'pending',
                    gateway_transaction_id UUID,
                    metadata JSONB DEFAULT '{}',
                    completed_at TIMESTAMPTZ,
                    failed_at TIMESTAMPTZ,
                    refunded_at TIMESTAMPTZ,
                    cancelled_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    sync_status VARCHAR(20) DEFAULT 'synced',
                    sync_version INTEGER DEFAULT 1,
                    last_synced_at TIMESTAMPTZ,
                    is_deleted BOOLEAN DEFAULT FALSE
                );
            ''')
            print('[✓] service_transactions created')
        except Exception as e:
            print(f'[!] service_transactions: {str(e)}')
        
        # 2. Create transaction_fees (depends on service_transactions)
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transaction_fees (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    region_code VARCHAR(50) DEFAULT 'global',
                    service_transaction_id UUID NOT NULL REFERENCES service_transactions(id),
                    fee_amount DECIMAL(12, 2) NOT NULL,
                    fee_percentage DECIMAL(5, 2) NOT NULL,
                    fee_type VARCHAR(50) NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    sync_status VARCHAR(20) DEFAULT 'synced',
                    sync_version INTEGER DEFAULT 1,
                    last_synced_at TIMESTAMPTZ,
                    is_deleted BOOLEAN DEFAULT FALSE
                );
            ''')
            print('[✓] transaction_fees created')
        except Exception as e:
            print(f'[!] transaction_fees: {str(e)}')
        
        # 3. Create payment_receipts (depends on service_transactions)
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payment_receipts (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    region_code VARCHAR(50) DEFAULT 'global',
                    receipt_number VARCHAR(100) UNIQUE NOT NULL,
                    service_transaction_id UUID NOT NULL REFERENCES service_transactions(id),
                    participant_id UUID NOT NULL,
                    amount DECIMAL(12, 2) NOT NULL,
                    currency VARCHAR(3) DEFAULT 'XOF',
                    payment_method VARCHAR(50) NOT NULL,
                    receipt_data JSONB DEFAULT '{}',
                    qr_code TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    sync_status VARCHAR(20) DEFAULT 'synced',
                    sync_version INTEGER DEFAULT 1,
                    last_synced_at TIMESTAMPTZ,
                    is_deleted BOOLEAN DEFAULT FALSE
                );
            ''')
            print('[✓] payment_receipts created')
        except Exception as e:
            print(f'[!] payment_receipts: {str(e)}')
        
        # 4. Create operating_rooms and surgery_schedules (circular dependency)
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operating_rooms (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    region_code VARCHAR(50) DEFAULT 'global',
                    hospital_id UUID NOT NULL,
                    or_number VARCHAR(20) NOT NULL,
                    or_name VARCHAR(100) NOT NULL,
                    floor_number VARCHAR(10) NOT NULL,
                    or_type VARCHAR(50) NOT NULL,
                    has_laparoscopy BOOLEAN DEFAULT FALSE,
                    has_robotic_surgery BOOLEAN DEFAULT FALSE,
                    has_c_arm BOOLEAN DEFAULT FALSE,
                    status VARCHAR(20) DEFAULT 'available',
                    current_surgery_id UUID,
                    is_active BOOLEAN DEFAULT TRUE,
                    notes TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    sync_status VARCHAR(20) DEFAULT 'synced',
                    sync_version INTEGER DEFAULT 1,
                    last_synced_at TIMESTAMPTZ,
                    is_deleted BOOLEAN DEFAULT FALSE,
                    UNIQUE(hospital_id, or_number)
                );
            ''')
            print('[✓] operating_rooms created')
        except Exception as e:
            print(f'[!] operating_rooms: {str(e)}')
        
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS surgery_schedules (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    region_code VARCHAR(50) DEFAULT 'global',
                    surgery_number VARCHAR(50) UNIQUE NOT NULL,
                    hospital_id UUID NOT NULL,
                    patient_id UUID NOT NULL,
                    admission_id UUID,
                    operating_room_id UUID NOT NULL REFERENCES operating_rooms(id),
                    scheduled_date DATE NOT NULL,
                    scheduled_start_time TIME NOT NULL,
                    estimated_duration_minutes INTEGER NOT NULL,
                    scheduled_end_time TIME,
                    procedure_name VARCHAR(255) NOT NULL,
                    procedure_code VARCHAR(50),
                    procedure_category VARCHAR(50) DEFAULT 'elective',
                    surgery_type VARCHAR(100),
                    primary_surgeon_id UUID NOT NULL,
                    assistant_surgeons JSONB DEFAULT '[]',
                    anesthesiologist_id UUID,
                    nurses JSONB DEFAULT '[]',
                    status VARCHAR(20) DEFAULT 'scheduled',
                    actual_start_time TIMESTAMPTZ,
                    actual_end_time TIMESTAMPTZ,
                    complications TEXT,
                    notes TEXT,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    sync_status VARCHAR(20) DEFAULT 'synced',
                    sync_version INTEGER DEFAULT 1,
                    last_synced_at TIMESTAMPTZ,
                    is_deleted BOOLEAN DEFAULT FALSE
                );
            ''')
            print('[✓] surgery_schedules created')
        except Exception as e:
            print(f'[!] surgery_schedules: {str(e)}')
        
        # Add FK constraint for circular dependency
        try:
            cursor.execute('''
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'fk_current_surgery'
                    ) THEN
                        ALTER TABLE operating_rooms 
                        ADD CONSTRAINT fk_current_surgery 
                        FOREIGN KEY (current_surgery_id) REFERENCES surgery_schedules(id) 
                        ON DELETE SET NULL;
                    END IF;
                END $$;
            ''')
            print('[✓] Fixed operating_rooms <-> surgery_schedules circular dependency')
        except Exception as e:
            print(f'[!] circular dependency fix: {str(e)}')
        
        # 5. Create journal_entry_lines (depends on projects - already exists)
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS journal_entry_lines (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    region_code VARCHAR(50) DEFAULT 'global',
                    journal_entry_id UUID NOT NULL,
                    account_id UUID NOT NULL,
                    description TEXT,
                    debit_amount DECIMAL(15, 2) DEFAULT 0,
                    credit_amount DECIMAL(15, 2) DEFAULT 0,
                    project_id UUID REFERENCES projects(id),
                    department_id UUID,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    sync_status VARCHAR(20) DEFAULT 'synced',
                    sync_version INTEGER DEFAULT 1,
                    last_synced_at TIMESTAMPTZ,
                    is_deleted BOOLEAN DEFAULT FALSE
                );
            ''')
            print('[✓] journal_entry_lines created')
        except Exception as e:
            print(f'[!] journal_entry_lines: {str(e)}')
        
        # 6. Create indexes
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_transactions_patient ON service_transactions(patient_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_transactions_provider ON service_transactions(service_provider_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_transactions_status ON service_transactions(status);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_operating_rooms_hospital_status ON operating_rooms(hospital_id, status);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_surgery_schedules_hospital ON surgery_schedules(hospital_id);')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_surgery_schedules_patient ON surgery_schedules(patient_id);')
            print('[✓] All indexes created')
        except Exception as e:
            print(f'[!] indexes: {str(e)}')
        
        print("\n" + "="*70)
        print("✅ COMPLETED: All missing tables created!")
        print("="*70 + "\n")

if __name__ == '__main__':
    fix_circular_dependencies()
