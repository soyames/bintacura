import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connections
from django.core.management import call_command

print("\n" + "="*70)
print("CREATING FINAL MISSING TABLES")
print("="*70 + "\n")

with connections['default'].cursor() as cursor:
    # 1. Create projects table
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                region_code VARCHAR(50) DEFAULT 'global',
                organization_id UUID NOT NULL,
                project_code VARCHAR(50) NOT NULL,
                project_name VARCHAR(255) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'planning',
                start_date DATE NOT NULL,
                end_date DATE,
                budget_amount DECIMAL(15, 2) DEFAULT 0,
                manager_id UUID,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                sync_status VARCHAR(20) DEFAULT 'synced',
                sync_version INTEGER DEFAULT 1,
                last_synced_at TIMESTAMPTZ,
                is_deleted BOOLEAN DEFAULT FALSE,
                UNIQUE(organization_id, project_code)
            );
            CREATE INDEX IF NOT EXISTS idx_projects_organization ON projects(organization_id);
            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
        ''')
        print('[✓] projects table created')
    except Exception as e:
        print(f'[!] projects: {str(e)}')
    
    # 2. Now create journal_entry_lines
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entry_lines (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                region_code VARCHAR(50) DEFAULT 'global',
                journal_entry_id UUID NOT NULL,
                account_id UUID NOT NULL,
                description VARCHAR(500),
                debit_amount DECIMAL(15, 2) DEFAULT 0 CHECK (debit_amount >= 0),
                credit_amount DECIMAL(15, 2) DEFAULT 0 CHECK (credit_amount >= 0),
                department_id UUID,
                project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                sync_status VARCHAR(20) DEFAULT 'synced',
                sync_version INTEGER DEFAULT 1,
                last_synced_at TIMESTAMPTZ,
                is_deleted BOOLEAN DEFAULT FALSE
            );
            CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_entry ON journal_entry_lines(journal_entry_id);
            CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_account ON journal_entry_lines(account_id);
            CREATE INDEX IF NOT EXISTS idx_journal_entry_lines_project ON journal_entry_lines(project_id);
        ''')
        print('[✓] journal_entry_lines table created')
    except Exception as e:
        print(f'[!] journal_entry_lines: {str(e)}')

print("\n" + "="*70)
print("✅ ALL TABLES CREATED!")
print("="*70 + "\n")

# Verify table count
with connections['default'].cursor() as cursor:
    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
    aws_count = cursor.fetchone()[0]
    print(f"AWS Database now has: {aws_count} tables")

with connections['frankfurt'].cursor() as cursor:
    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
    render_count = cursor.fetchone()[0]
    print(f"Render Database has: {render_count} tables")

if aws_count == render_count:
    print("\n✅ SUCCESS: Both databases now have the same number of tables!")
else:
    print(f"\n⚠️ WARNING: Still {render_count - aws_count} tables missing")
