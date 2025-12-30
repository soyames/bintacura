import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connections

def migrate_in_order():
    """Migrate data respecting foreign key dependencies"""
    
    # Order matters - parent tables first
    migration_order = [
        # Core identity tables
        'auth_group',
        'auth_permission',
        'django_content_type',
        'participants',
        'patient_data',
        'doctor_data',
        'hospital_data',
        'insurance_company_data',
        
        # Dependent on participants
        'participant_phones',
        'participant_preferences',
        'participant_profiles',
        'participant_activity_logs',
        'emergency_contacts',
        'legal_representatives',
        'dependent_profiles',
        'online_status',
        
        # Financial
        'core_wallets',
        'payment_methods',
        'participant_payment_methods',
        
        # Appointments
        'availabilities',
        'doctor_services',
        'participant_services',
        'appointments',
        'appointment_services',
        
        # Prescriptions
        'prescriptions',
        'prescription_items',
        'prescription_fulfillments',
        'fulfillment_items',
        
        # Everything else can follow
    ]
    
    render_conn = connections['frankfurt']
    aws_conn = connections['default']
    
    print(f"\n{'='*70}")
    print("ORDERED DATA MIGRATION: Render → AWS")
    print(f"{'='*70}\n")
    
    for table in migration_order:
        try:
            # Check if table exists in both databases
            with render_conn.cursor() as c:
                c.execute(f"SELECT COUNT(*) FROM \"{table}\"")
                render_count = c.fetchone()[0]
            
            with aws_conn.cursor() as c:
                c.execute(f"SELECT COUNT(*) FROM \"{table}\"")
                aws_count = c.fetchone()[0]
            
            if render_count == 0:
                print(f"  [SKIP] {table}: empty in Render")
                continue
            
            if aws_count > 0:
                print(f"  [EXISTS] {table}: {aws_count} rows in AWS, {render_count} in Render")
                continue
            
            # Get column names
            with render_conn.cursor() as c:
                c.execute(f"SELECT * FROM \"{table}\" LIMIT 0")
                render_columns = [desc[0] for desc in c.description]
            
            with aws_conn.cursor() as c:
                c.execute(f"SELECT * FROM \"{table}\" LIMIT 0")
                aws_columns = [desc[0] for desc in c.description]
            
            # Only use common columns
            common_columns = list(set(render_columns) & set(aws_columns))
            
            if not common_columns:
                print(f"  [ERROR] {table}: no common columns")
                continue
            
            # Copy data
            with render_conn.cursor() as c:
                column_list = ','.join([f'"{col}"' for col in common_columns])
                c.execute(f'SELECT {column_list} FROM \"{table}\"')
                rows = c.fetchall()
            
            if rows:
                placeholders = ','.join(['%s'] * len(common_columns))
                column_names = ','.join([f'"{col}"' for col in common_columns])
                
                with aws_conn.cursor() as c:
                    c.executemany(
                        f'INSERT INTO \"{table}\" ({column_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING',
                        rows
                    )
                
                print(f"  [MIGRATED] {table}: {len(rows)} rows")
        
        except Exception as e:
            print(f"  [ERROR] {table}: {str(e)[:100]}")
    
    print(f"\n{'='*70}\n")

if __name__ == '__main__':
    migrate_in_order()
