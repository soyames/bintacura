import os
import sys
import django

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection, transaction
from django.apps import apps

def create_table_in_order():
    """Create remaining tables in dependency order"""
    
    # Models to create in order
    models_in_order = [
        ('hospital', 'SurgerySchedule'),
        ('hospital', 'OperatingRoom'),
        ('financial', 'ProjectManagement'),
        ('financial', 'JournalEntryLine'),
        ('payments', 'GatewayTransaction'),
        ('payments', 'ServiceTransaction'),
        ('payments', 'TransactionFee'),
        ('payments', 'PaymentReceipt'),
    ]
    
    created = []
    errors = []
    
    for app_label, model_name in models_in_order:
        try:
            with transaction.atomic():
                model = apps.get_model(app_label, model_name)
                table_name = model._meta.db_table
                
                # Check if table exists
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = %s
                        );
                    """, [table_name])
                    exists = cursor.fetchone()[0]
                    
                    if not exists:
                        # Create the table
                        with connection.schema_editor() as schema_editor:
                            schema_editor.create_model(model)
                        print(f"✅ Created: {table_name}")
                        created.append(table_name)
                    else:
                        print(f"⏭️  Exists: {table_name}")
        except Exception as e:
            print(f"❌ Error creating {app_label}.{model_name}: {str(e)}")
            errors.append((app_label, model_name, str(e)))
    
    print(f"\n{'='*70}")
    print(f"Created: {len(created)} tables")
    print(f"Errors: {len(errors)} tables")
    print(f"{'='*70}")

if __name__ == '__main__':
    create_table_in_order()
