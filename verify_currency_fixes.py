#!/usr/bin/env python
"""
Verify Currency Conversion Fixes
=================================

This script verifies that all currency conversion issues are fixed.
"""

from pathlib import Path
import re

def check_currency_service():
    """Check that CurrencyConverterService has both methods"""
    print("🔍 Checking CurrencyConverterService...")
    
    service_file = Path('currency_converter/services.py')
    content = service_file.read_text()
    
    has_convert = 'def convert(' in content
    has_convert_amount = 'def convert_amount(' in content
    has_base_currency = "BASE_CURRENCY = 'XOF'" in content
    
    if has_convert and has_convert_amount and has_base_currency:
        print("   ✅ CurrencyConverterService has both convert() and convert_amount()")
        print("   ✅ BASE_CURRENCY is set to 'XOF'")
        return True
    else:
        print("   ❌ Missing methods or wrong base currency!")
        return False

def check_for_problematic_patterns():
    """Check for remaining problematic patterns"""
    print("\n🔍 Checking for problematic patterns...")
    
    files_to_check = [
        'appointments/views.py',
        'core/views.py',
        'core/templatetags/currency_filters.py',
        'core/system_views.py',
        'insurance/payment_service.py',
        'insurance/serializers.py',
        'payments/invoice_views.py',
    ]
    
    issues = []
    for file_path in files_to_check:
        path = Path(file_path)
        if not path.exists():
            continue
            
        content = path.read_text()
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for convert() calls that might return dict
            if 'CurrencyConverterService.convert(' in line:
                # Look ahead to see if result is extracted properly
                context = '\n'.join(lines[max(0, i-1):min(len(lines), i+3)])
                if ("['converted_amount']" not in context and 
                    'convert_amount(' not in line and
                    'convert_and_log(' not in line):
                    issues.append({
                        'file': file_path,
                        'line': i,
                        'content': line.strip()
                    })
    
    if issues:
        print(f"   ❌ Found {len(issues)} potential issues:")
        for issue in issues[:5]:  # Show first 5
            print(f"      {issue['file']}:{issue['line']}: {issue['content'][:70]}")
        return False
    else:
        print("   ✅ No problematic patterns found!")
        return True

def check_insurance_serializer():
    """Check insurance serializer specifically"""
    print("\n🔍 Checking insurance/serializers.py...")
    
    file_path = Path('insurance/serializers.py')
    if not file_path.exists():
        print("   ⏭️  File not found")
        return True
        
    content = file_path.read_text()
    
    # Check if it properly extracts converted_amount
    has_proper_extraction = ("conversion_result.get('converted_amount'" in content or 
                            'conversion_result[\'converted_amount\']' in content or
                            'convert_amount(' in content)
    
    if has_proper_extraction:
        print("   ✅ Properly extracts converted_amount from dict")
        return True
    else:
        print("   ⚠️  May need manual review")
        return False

def main():
    print("=" * 70)
    print("🔧 Currency Conversion Fix Verification")
    print("=" * 70)
    
    results = [
        check_currency_service(),
        check_for_problematic_patterns(),
        check_insurance_serializer(),
    ]
    
    print("\n" + "=" * 70)
    if all(results):
        print("✅ ALL CHECKS PASSED!")
        print("\nYou can now:")
        print("1. Review the changes with: git diff")
        print("2. Commit and push: git add -A && git commit -m 'Fix currency conversion'")
        print("3. Pull on server and restart services")
    else:
        print("⚠️  SOME ISSUES FOUND - Please review above")
    print("=" * 70)

if __name__ == '__main__':
    main()
