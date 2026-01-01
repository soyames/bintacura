#!/usr/bin/env python3
"""
Fix all incorrect usages of CurrencyConverterService.convert()

The convert() method returns a dict with keys:
{
    'original_amount': Decimal,
    'converted_amount': Decimal,
    'from_currency': str,
    'to_currency': str,
    'rate': Decimal,
}

This script finds and fixes all places where the result is used incorrectly.
"""

import re
import os
from pathlib import Path

def fix_convert_usage_in_file(filepath):
    """Fix CurrencyConverterService.convert() usage in a file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = []
    
    # Pattern 1: variable = CurrencyConverterService.convert(...)
    # Followed by: float(variable) or use of variable as number
    
    # Find all convert calls and store their variable names
    convert_pattern = r'(\w+)\s*=\s*CurrencyConverterService\.convert\('
    matches = list(re.finditer(convert_pattern, content))
    
    for match in matches:
        var_name = match.group(1)
        
        # Check if this variable is later used as float(var_name) or directly as number
        # Pattern: float(var_name)
        float_usage = rf'float\({var_name}\)'
        if re.search(float_usage, content):
            # Replace float(var_name) with float(var_name['converted_amount'])
            content = re.sub(
                rf'float\({var_name}\)',
                rf"float({var_name}['converted_amount'])",
                content
            )
            changes_made.append(f"Fixed float({var_name}) -> float({var_name}['converted_amount'])")
        
        # Pattern: "balance": converted_balance (direct dict assignment)
        # This should become: "balance": converted_balance['converted_amount']
        direct_usage_pattern = rf'["\'][\w_]+["\']\s*:\s*{var_name}(?!\[)'
        if re.search(direct_usage_pattern, content):
            # Only replace if not already accessing dict
            content = re.sub(
                rf'(["\'][\w_]+["\']\s*:\s*)({var_name})(?!\[)',
                rf"\1\2['converted_amount']",
                content
            )
            changes_made.append(f"Fixed direct usage: {var_name} -> {var_name}['converted_amount']")
    
    if content != original_content:
        # Create backup
        backup_path = str(filepath) + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # Write fixed content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True, changes_made
    
    return False, []

def main():
    """Main function to fix all files"""
    print("🔧 Fixing CurrencyConverterService.convert() usage...")
    print("=" * 60)
    
    # Files to check (from grep results)
    files_to_check = [
        'core/views.py',
        'core/system_views.py',
        'core/templatetags/currency_filters.py',
        'appointments/views.py',
        'transport/views.py',
        'prescriptions/views.py',
        'pharmacy/cart_views.py',
        'pharmacy/payment_views.py',
        'insurance/payment_service.py',
        'payments/universal_payment_views.py',
        'payments/invoice_views.py',
        'payments/orchestration_service.py',
    ]
    
    base_dir = Path(__file__).parent
    fixed_files = []
    
    for file_path in files_to_check:
        full_path = base_dir / file_path
        if full_path.exists():
            print(f"\n📄 Checking: {file_path}")
            fixed, changes = fix_convert_usage_in_file(full_path)
            if fixed:
                print(f"   ✅ Fixed! Changes:")
                for change in changes:
                    print(f"      - {change}")
                fixed_files.append(file_path)
            else:
                print(f"   ⏭️  No changes needed")
        else:
            print(f"   ⚠️  File not found: {file_path}")
    
    print("\n" + "=" * 60)
    if fixed_files:
        print(f"✅ Fixed {len(fixed_files)} files:")
        for f in fixed_files:
            print(f"   - {f}")
        print("\n📝 Backups created with .backup extension")
    else:
        print("✅ No files needed fixing!")
    
    print("\n⚠️  Please review the changes and test thoroughly!")

if __name__ == '__main__':
    main()
