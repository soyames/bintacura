"""
Verification script for authentication and database fixes
Tests all implemented fixes before deployment
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings
from django.db import connection

def print_section(title):
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")

def test_1_settings_configuration():
    """Test 1: Verify settings have default consultation fee"""
    print_section("TEST 1: Settings Configuration")
    
    try:
        default_fee = getattr(settings, 'DEFAULT_CONSULTATION_FEE_XOF', None)
        if default_fee:
            print(f"✅ DEFAULT_CONSULTATION_FEE_XOF found: {default_fee} XOF")
            print(f"   Stored in cents: {default_fee * 100}")
            return True
        else:
            print("❌ DEFAULT_CONSULTATION_FEE_XOF not found in settings")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_2_authentication_views():
    """Test 2: Check authentication views have fixes"""
    print_section("TEST 2: Authentication Views")
    
    try:
        with open('authentication/views.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        tests = {
            'Phone error handling': 'except Exception as phone_error:',
            'Doctor default fee': 'default_fee_xof = getattr(settings',
            'Hospital creation': "elif user.role == 'hospital':",
            'HospitalData import': 'from hospital.models import HospitalData',
        }
        
        results = []
        for test_name, search_string in tests.items():
            if search_string in content:
                print(f"✅ {test_name}: Found")
                results.append(True)
            else:
                print(f"❌ {test_name}: Not found")
                results.append(False)
        
        return all(results)
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_3_hospital_model():
    """Test 3: Verify HospitalData model exists"""
    print_section("TEST 3: Hospital Model")
    
    try:
        from hospital.models import HospitalData
        print("✅ HospitalData model imported successfully")
        
        # Check fields
        fields = [f.name for f in HospitalData._meta.get_fields()]
        required_fields = ['participant', 'consultation_fee', 'license_number', 'bed_capacity']
        
        for field in required_fields:
            if field in fields:
                print(f"✅ Field '{field}' exists")
            else:
                print(f"❌ Field '{field}' missing")
                return False
        
        return True
    except ImportError as e:
        print(f"❌ Cannot import HospitalData: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_4_migrations_exist():
    """Test 4: Check migration files exist"""
    print_section("TEST 4: Migration Files")
    
    migrations = [
        ('doctor', '0006_set_default_consultation_fee.py'),
        ('hospital', '0007_hospitaldata.py'),
        ('hospital', '0008_set_default_hospital_fees.py'),
    ]
    
    results = []
    for app, filename in migrations:
        path = os.path.join(app, 'migrations', filename)
        if os.path.exists(path):
            print(f"✅ {path}: Exists")
            results.append(True)
        else:
            print(f"❌ {path}: Not found")
            results.append(False)
    
    return all(results)

def test_5_migrations_use_settings():
    """Test 5: Verify migrations use settings not hardcoded values"""
    print_section("TEST 5: Migrations Use Settings")
    
    migration_files = [
        'doctor/migrations/0006_set_default_consultation_fee.py',
        'hospital/migrations/0008_set_default_hospital_fees.py',
    ]
    
    results = []
    for filepath in migration_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'getattr(settings' in content and 'DEFAULT_CONSULTATION_FEE_XOF' in content:
                print(f"✅ {filepath}: Uses settings")
                results.append(True)
            else:
                print(f"❌ {filepath}: Hardcoded values found")
                results.append(False)
        except Exception as e:
            print(f"❌ {filepath}: Error - {e}")
            results.append(False)
    
    return all(results)

def test_6_check_database_command():
    """Test 6: Verify check_database command exists"""
    print_section("TEST 6: Check Database Command")
    
    command_path = 'core/management/commands/check_database.py'
    if os.path.exists(command_path):
        print(f"✅ {command_path}: Exists")
        
        try:
            with open(command_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = {
                'Database connection check': 'check_connection',
                'Table existence check': 'check_critical_tables',
                'Participant check': 'check_participants',
                'Doctor fee check': 'check_doctor_fees',
            }
            
            for check_name, search_string in checks.items():
                if search_string in content:
                    print(f"✅ {check_name}: Implemented")
                else:
                    print(f"⚠️  {check_name}: Not found")
            
            return True
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return False
    else:
        print(f"❌ {command_path}: Not found")
        return False

def test_7_database_connectivity():
    """Test 7: Check database connection"""
    print_section("TEST 7: Database Connectivity")
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✅ Database connected: {version.split(',')[0]}")
            
            # Check if critical tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('core_participants', 'doctor_data', 'patient_data')
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            for table in tables:
                print(f"✅ Table exists: {table[0]}")
            
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_8_documentation():
    """Test 8: Verify documentation files exist"""
    print_section("TEST 8: Documentation")
    
    docs = [
        'docs/authentication-and-database-fixes-todo.md',
        'docs/authentication-and-database-fixes-summary.md',
        'docs/IMPLEMENTATION_FINAL_REPORT.md',
        'docs/QUICK_DEPLOYMENT_GUIDE.md',
    ]
    
    results = []
    for doc in docs:
        if os.path.exists(doc):
            size = os.path.getsize(doc)
            print(f"✅ {doc}: Exists ({size:,} bytes)")
            results.append(True)
        else:
            print(f"❌ {doc}: Not found")
            results.append(False)
    
    return all(results)

def main():
    """Run all tests"""
    print_section("BINTACURA - IMPLEMENTATION VERIFICATION")
    print("Testing all fixes before deployment...")
    
    tests = [
        test_1_settings_configuration,
        test_2_authentication_views,
        test_3_hospital_model,
        test_4_migrations_exist,
        test_5_migrations_use_settings,
        test_6_check_database_command,
        test_7_database_connectivity,
        test_8_documentation,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print_section("VERIFICATION SUMMARY")
    passed = sum(results)
    total = len(results)
    percentage = (passed / total) * 100 if total > 0 else 0
    
    print(f"Tests Passed: {passed}/{total} ({percentage:.1f}%)")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - READY FOR DEPLOYMENT")
        return 0
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED - FIX ISSUES BEFORE DEPLOYMENT")
        return 1

if __name__ == '__main__':
    sys.exit(main())
