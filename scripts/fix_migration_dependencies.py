"""
Fix migration dependency conflicts by resetting inconsistent migration state.
This script handles the issue where ai.0001_initial was applied before doctor.0005_alter_doctorservice_currency
"""

import os
import sys
import django

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection, connections
from django.db.migrations.recorder import MigrationRecorder

def fix_migration_dependencies():
    """Fix migration dependency conflicts across all databases"""
    
    # Get all database aliases
    database_aliases = list(connections.databases.keys())
    
    print("\n" + "="*70)
    print("FIXING MIGRATION DEPENDENCIES")
    print("="*70)
    
    for db_alias in database_aliases:
        print(f"\n>>> Processing database: {db_alias.upper()}")
        
        try:
            # Get the migration recorder for this database
            recorder = MigrationRecorder(connections[db_alias])
            
            # Check for all ai migrations
            ai_migrations = recorder.migration_qs.filter(app='ai')
            
            if ai_migrations.exists():
                count = ai_migrations.count()
                print(f"  [INFO] Found {count} ai migration(s) - will be removed and reapplied")
                
                # Remove all ai migration records
                recorder.migration_qs.filter(app='ai').delete()
                print(f"  [SUCCESS] Removed all ai migration records from {db_alias}")
            else:
                print(f"  [INFO] No ai migrations found in {db_alias}")
                
        except Exception as e:
            print(f"  [ERROR] Failed to process {db_alias}: {str(e)}")
            continue
    
    print("\n" + "="*70)
    print("MIGRATION DEPENDENCY FIX COMPLETED")
    print("="*70)
    print("\nNext steps:")
    print("1. Run: python manage.py migrate ai --fake-initial")
    print("2. Run: python manage.py migrate --all")
    print("="*70 + "\n")

if __name__ == '__main__':
    fix_migration_dependencies()
