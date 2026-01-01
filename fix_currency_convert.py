#!/usr/bin/env python3
"""
Fix currency converter usage across the codebase.
The convert() method returns a dict with 'converted_amount' key,
but many places expect it to return a number directly.
"""

import re
import os
from pathlib import Path

# Files to fix
FILES_TO_FIX = [
    'transport/serializers.py',
    'transport/views.py',
    'core/views.py',
    'core/system_views.py',
    'core/templatetags/currency_filters.py',
    'insurance/payment_service.py',
    'prescriptions/views.py',
    'payments/invoice_views.py',
    'payments/universal_payment_views.py',
    'payments/orchestration_service.py',
    'pharmacy/payment_views.py',
    'pharmacy/cart_views.py',
]

def fix_currency_convert_usage(file_path):
    """Fix CurrencyConverterService.convert() usage in a file"""
    print(f"Processing {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        modifications = 0
        
        # Pattern: variable = CurrencyConverterService.convert(...)
        # where the result is used directly as a number
        
        # Find all convert() calls and check context
        pattern = r'(\s*)(\w+)\s*=\s*CurrencyConverterService\.convert\('
        
        def check_and_fix(match):
            nonlocal modifications
            indent = match.group(1)
            var_name = match.group(2)
            
            # Get surrounding context
            start = match.start()
            # Check next few lines to see if variable is used as number
            next_200_chars = content[match.end():match.end()+200]
            
            # If we see float(var_name) or similar number usage, need to extract converted_amount
            if (f'float({var_name})' in next_200_chars or 
                f'{var_name},' in next_200_chars or
                f'{var_name})' in next_200_chars):
                
                # Check if already fixed
                prev_50 = content[max(0, start-100):start]
                if 'conversion_result' in prev_50 or "_result = " in prev_50:
                    return match.group(0)  # Already fixed
                
                modifications += 1
                # Change to: var_name_result = CurrencyConverterService.convert(
                # Then add: var_name = var_name_result['converted_amount']
                return f"{indent}{var_name}_result = CurrencyConverterService.convert("
            
            return match.group(0)
        
        # First pass: rename variables
        new_content = re.sub(pattern, check_and_fix, content)
        
        if modifications > 0:
            print(f"  Found {modifications} usages to fix")
            # Second pass: add extraction lines
            # This is complex, so let's do it manually for critical files
            print(f"  ⚠️  Manual fix required - pattern found but complex to auto-fix")
            return False
        
        print(f"  ✓ No issues found or already fixed")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

if __name__ == '__main__':
    base_dir = Path(__file__).parent
    print(f"Base directory: {base_dir}\n")
    
    for file_rel_path in FILES_TO_FIX:
        file_path = base_dir / file_rel_path
        if file_path.exists():
            fix_currency_convert_usage(file_path)
        else:
            print(f"File not found: {file_path}")
        print()
