import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connections

with connections['default'].cursor() as cursor:
    # Check if projects table exists
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='projects';")
    result = cursor.fetchone()
    print(f'Projects table exists: {result is not None}')
    
    if result:
        # Create journal_entry_lines with proper FK
        try:
            cursor.execute('''
                DROP TABLE IF EXISTS journal_entry_lines CASCADE;
                CREATE TABLE journal_entry_lines (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    region_code VARCHAR(50) DEFAULT 'global',
                    journal_entry_id UUID NOT NULL,
                    account_id UUID NOT NULL,
                    description TEXT,
                    debit_amount DECIMAL(15, 2) DEFAULT 0,
                    credit_amount DECIMAL(15, 2) DEFAULT 0,
                    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                    department_id UUID,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    sync_status VARCHAR(20) DEFAULT 'synced',
                    sync_version INTEGER DEFAULT 1,
                    last_synced_at TIMESTAMPTZ,
                    is_deleted BOOLEAN DEFAULT FALSE
                );
                CREATE INDEX idx_journal_entry_lines_entry ON journal_entry_lines(journal_entry_id);
                CREATE INDEX idx_journal_entry_lines_account ON journal_entry_lines(account_id);
            ''')
            print('[✓] journal_entry_lines created successfully!')
        except Exception as e:
            print(f'[ERROR] {e}')
    else:
        print('[ERROR] Projects table does not exist yet')
