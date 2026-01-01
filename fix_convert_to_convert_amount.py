#!/usr/bin/env python
"""
Fix all CurrencyConverterService.convert() calls that should use convert_amount()

This will replace:
  CurrencyConverterService.convert(amount, from, to)
with:
  CurrencyConverterService.convert_amount(amount, from, to)

Only in places where the result is used directly (not extracting converted_amount from dict)
"""

import re
from pathlib import Path

FILES_TO_FIX = [
    'appointments/views.py',
    'core/views.py',
    'core/templatetags/currency_filters.py',
    'core/system_views.py',
    'insurance/payment_service.py',
    'payments/invoice_views.py',
]

def fix_file(file_path):
    """Fix a single file"""
    full_path = Path(file_path)
    if not full_path.exists():
        print(f"⏭️  Skipping {file_path} (not found)")
        return False
        
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
        original_content = content
    
    # Pattern: Find convert() calls where result is NOT accessed with ['converted_amount']
    # Look for patterns like:
    # 1. result = CurrencyConverterService.convert(...)\n    (no ['converted_amount'] in next lines)
    # 2. float(CurrencyConverterService.convert(...))
    # 3. Decimal(CurrencyConverterService.convert(...))
    
    changes_made = 0
    
    # Fix pattern 1: Direct assignment without extracting dict value
    # But be careful not to replace if next line has ['converted_amount']
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        new_line = line
        
        # Check if this line has a convert() call
        if 'CurrencyConverterService.convert(' in line:
            # Look ahead to see if result is used directly (not as dict)
            next_lines = '\n'.join(lines[i:min(i+5, len(lines))])
            
            # If we don't see ['converted_amount'] extraction in next few lines,
            # and we see direct usage (float, Decimal, math operations), fix it
            if ("[' converted_amount']" not in next_lines and 
                "['converted_amount']" not in next_lines and
                ('float(' in next_lines or 'Decimal(' in next_lines or
                 ' + ' in next_lines or ' - ' in next_lines or 
                 ' * ' in next_lines or ' / ' in next_lines or
                 'CurrencyConverterService.format_amount(' in next_lines)):
                
                # Replace .convert( with .convert_amount(
                new_line = line.replace('CurrencyConverterService.convert(', 
                                       'CurrencyConverterService.convert_amount(')
                if new_line != line:
                    changes_made += 1
                    print(f"   Line {i+1}: {line.strip()[:80]}")
                    print(f"        → {new_line.strip()[:80]}")
        
        new_lines.append(new_line)
    
    if changes_made > 0:
        new_content = '\n'.join(new_lines)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ {file_path}: Fixed {changes_made} calls\n")
        return True
    else:
        print(f"⏭️  {file_path}: No changes needed\n")
        return False

def main():
    print("🔧 Fixing CurrencyConverterService.convert() → convert_amount()")
    print("=" * 70)
    
    files_fixed = 0
    total_changes = 0
    
    for file_path in FILES_TO_FIX:
        if fix_file(file_path):
            files_fixed += 1
    
    print("=" * 70)
    print(f"✅ Fixed {files_fixed} files")
    print("\n📋 Next Steps:")
    print("   1. Review the changes above")
    print("   2. Test locally")
    print("   3. Push to server")
    print("   4. Restart services: sudo systemctl restart bintacura")

if __name__ == '__main__':
    main()
