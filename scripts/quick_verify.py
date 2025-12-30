"""
Simple file-based verification script
Checks if all fixes are implemented without Django setup
"""
import os
import sys

def print_section(title):
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")

def check_file_content(filepath, search_patterns, test_name):
    """Check if file contains expected patterns"""
    print(f"\n{test_name}:")
    if not os.path.exists(filepath):
        print(f"  ❌ File not found: {filepath}")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        results = []
        for pattern_name, pattern in search_patterns.items():
            if pattern in content:
                print(f"  ✅ {pattern_name}")
                results.append(True)
            else:
                print(f"  ❌ {pattern_name} - NOT FOUND")
                results.append(False)
        
        return all(results)
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return False

def main():
    print_section("BINTACURA - QUICK VERIFICATION")
    
    all_tests = []
    
    # Test 1: Settings
    print_section("1. SETTINGS CONFIGURATION")
    result = check_file_content(
        'backend/settings.py',
        {
            'Default fee defined': "'DEFAULT_CONSULTATION_FEE_XOF': 3500",
        },
        "Settings File"
    )
    all_tests.append(result)
    
    # Test 2: Authentication views
    print_section("2. AUTHENTICATION VIEWS")
    result = check_file_content(
        'authentication/views.py',
        {
            'Phone error handling': 'except Exception as phone_error:',
            'Doctor default fee': 'default_fee_xof = getattr(settings',
            'Hospital creation': "elif user.role == 'hospital':",
            'HospitalData import': 'from hospital.models import HospitalData',
            'Consultation fee cents': 'consultation_fee_cents = default_fee_xof * 100',
        },
        "Authentication Views"
    )
    all_tests.append(result)
    
    # Test 3: Hospital model
    print_section("3. HOSPITAL MODEL")
    result = check_file_content(
        'hospital/models.py',
        {
            'HospitalData class': 'class HospitalData(models.Model):',
            'Consultation fee field': 'consultation_fee = models.IntegerField',
            'License number': 'license_number = models.CharField',
            'Rating system': 'def get_actual_rating(self):',
        },
        "Hospital Model"
    )
    all_tests.append(result)
    
    # Test 4: Doctor migration
    print_section("4. DOCTOR MIGRATION")
    result = check_file_content(
        'doctor/migrations/0006_set_default_consultation_fee.py',
        {
            'Uses settings': 'getattr(settings',
            'DEFAULT_CONSULTATION_FEE_XOF': 'DEFAULT_CONSULTATION_FEE_XOF',
            'Converts to cents': 'default_fee_xof * 100',
        },
        "Doctor Migration"
    )
    all_tests.append(result)
    
    # Test 5: Hospital migrations
    print_section("5. HOSPITAL MIGRATIONS")
    result1 = check_file_content(
        'hospital/migrations/0007_hospitaldata.py',
        {
            'Creates HospitalData': 'CreateModel',
            'consultation_fee field': 'consultation_fee',
        },
        "Hospital Data Creation Migration"
    )
    
    result2 = check_file_content(
        'hospital/migrations/0008_set_default_hospital_fees.py',
        {
            'Uses settings': 'getattr(settings',
            'DEFAULT_CONSULTATION_FEE_XOF': 'DEFAULT_CONSULTATION_FEE_XOF',
            'Converts to cents': 'default_fee_xof * 100',
        },
        "Hospital Default Fees Migration"
    )
    all_tests.append(result1 and result2)
    
    # Test 6: Check database command
    print_section("6. DATABASE HEALTH CHECK COMMAND")
    result = check_file_content(
        'core/management/commands/check_database.py',
        {
            'Command class': 'class Command(BaseCommand):',
            'Check connection': 'def check_connection',
            'Check tables': 'def check_critical_tables',
            'Check fees': 'def check_doctor_fees',
        },
        "Check Database Command"
    )
    all_tests.append(result)
    
    # Test 7: Documentation
    print_section("7. DOCUMENTATION FILES")
    docs = {
        'TODO': 'docs/authentication-and-database-fixes-todo.md',
        'Summary': 'docs/authentication-and-database-fixes-summary.md',
        'Final Report': 'docs/IMPLEMENTATION_FINAL_REPORT.md',
        'Quick Guide': 'docs/QUICK_DEPLOYMENT_GUIDE.md',
    }
    
    doc_results = []
    for doc_name, doc_path in docs.items():
        if os.path.exists(doc_path):
            size = os.path.getsize(doc_path)
            print(f"  ✅ {doc_name}: {doc_path} ({size:,} bytes)")
            doc_results.append(True)
        else:
            print(f"  ❌ {doc_name}: {doc_path} NOT FOUND")
            doc_results.append(False)
    all_tests.append(all(doc_results))
    
    # Summary
    print_section("SUMMARY")
    passed = sum(all_tests)
    total = len(all_tests)
    percentage = (passed / total) * 100 if total > 0 else 0
    
    print(f"Tests Passed: {passed}/{total} ({percentage:.1f}%)\n")
    
    if passed == total:
        print("✅ ALL CHECKS PASSED!")
        print("\nNext steps:")
        print("1. Apply migrations: python manage.py migrate")
        print("2. Test registration and login")
        print("3. Verify fee displays")
        return 0
    else:
        print(f"⚠️  {total - passed} CHECK(S) FAILED")
        print("\nPlease review the failed checks above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
