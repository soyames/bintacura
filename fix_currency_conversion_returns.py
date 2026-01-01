#!/usr/bin/env python
"""
Fix all CurrencyConverterService.convert() usages to handle dict return value.

ISSUE: CurrencyConverterService.convert() returns a dict with:
{
    'original_amount': Decimal,
    'converted_amount': Decimal,  # <- We need this value
    'from_currency': str,
    'to_currency': str,
    'rate': Decimal,
}

But many places in code expect just a Decimal/float value.

This script will search and display all usages that need fixing.
"""

import os
import re
from pathlib import Path

# Files to check (from grep results)
FILES_TO_CHECK = [
    'currency_converter/views.py',
    'transport/views.py',
    'transport/serializers.py',
    'appointments/views.py',
    'core/views.py',
    'core/templatetags/currency_filters.py',
    'core/system_views.py',
    'prescriptions/views.py',
    'pharmacy/payment_views.py',
    'pharmacy/cart_views.py',
    'payments/universal_payment_views.py',
    'payments/receipt_service.py',
    'payments/payment_orchestration_service.py',
    'payments/orchestration_service.py',
    'insurance/serializers.py',
    'insurance/payment_service.py',
    'payments/invoice_views.py',
]

def find_convert_usages():
    """Find all CurrencyConverterService.convert() usages"""
    print("🔍 Searching for CurrencyConverterService.convert() usages...")
    print("=" * 70)
    
    issues_found = []
    
    for file_path in FILES_TO_CHECK:
        full_path = Path(file_path)
        if not full_path.exists():
            continue
            
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
        # Find convert() calls
        for i, line in enumerate(lines, 1):
            if 'CurrencyConverterService.convert(' in line and 'converted_amount' not in line:
                # Check if the result is being used directly (not extracting converted_amount)
                # Look at next few lines to see how it's used
                context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                
                # Check for problematic patterns
                if any(pattern in context for pattern in ['float(', 'Decimal(', '* ', '+ ', '- ', '/ ']):
                    issues_found.append({
                        'file': file_path,
                        'line': i,
                        'context': context
                    })
    
    if issues_found:
        print(f"\n❌ Found {len(issues_found)} potential issues:\n")
        for issue in issues_found:
            print(f"📄 {issue['file']}:{issue['line']}")
            print(f"   Context:")
            print("   " + issue['context'].replace('\n', '\n   '))
            print()
    else:
        print("\n✅ No obvious issues found!")
        print("   All usages seem to handle the dict return value correctly.")
    
    return issues_found

def show_fix_examples():
    """Show examples of correct usage"""
    print("\n" + "=" * 70)
    print("✅ CORRECT USAGE PATTERNS:")
    print("=" * 70)
    print("""
1. Extract converted_amount from dict:
   ✅ result = CurrencyConverterService.convert(amount, from_cur, to_cur)
   ✅ converted = result['converted_amount']
   
2. Use convert_to_local_currency (returns tuple):
   ✅ converted, currency = CurrencyConverterService.convert_to_local_currency(amount_xof, participant)
   
3. Use convert_from_local_currency (returns Decimal):
   ✅ amount_xof = CurrencyConverterService.convert_from_local_currency(amount_local, local_currency)

❌ WRONG USAGE:
   ❌ converted = CurrencyConverterService.convert(amount, from_cur, to_cur)
   ❌ total = float(converted)  # ERROR: converted is dict, not Decimal!
   
   ❌ converted = CurrencyConverterService.convert(amount, from_cur, to_cur)
   ❌ total = converted * 2  # ERROR: can't multiply dict!
""")

if __name__ == '__main__':
    issues = find_convert_usages()
    show_fix_examples()
    
    if issues:
        print(f"\n⚠️  Found {len(issues)} files that may need fixing")
        print("    Review the context above and update code to extract 'converted_amount' from dict")
    else:
        print("\n✅ All CurrencyConverterService.convert() usages look good!")
