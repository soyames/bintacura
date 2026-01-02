"""
Script to add type hints to SerializerMethodField methods
Fixes DRF Spectacular W001 warnings
"""

import re
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(r'C:\Users\soyam\Documents\GitHub\bintacura')

# Files to process
SERIALIZER_FILES = [
    'communication/serializers.py',
    'core/serializers.py',
    'doctor/serializers.py',
    'financial/serializers.py',
    'health_records/serializers.py',
    'hospital/serializers.py',
    'hr/serializers.py',
    'insurance/serializers.py',
    'patient/serializers.py',
    'payments/serializers.py',
    'pharmacy/serializers.py',
    'prescriptions/serializers.py',
    'transport/serializers.py',
]

# Common return type patterns
RETURN_TYPE_PATTERNS = {
    r'return\s+{\s*["\']': ' -> dict:',  # Returns dict
    r'return\s+\[\s*': ' -> list:',  # Returns list
    r'return\s+(True|False)': ' -> bool:',  # Returns bool
    r'return\s+\d+': ' -> int:',  # Returns int
    r'return\s+float': ' -> float:',  # Returns float
    r'return\s+["\']': ' -> str:',  # Returns string
}

def analyze_method_return_type(method_body):
    """Analyze method body to determine return type"""
    # Check for dictionary return
    if re.search(r'return\s+{', method_body):
        return ' -> dict:'
    # Check for list return
    if re.search(r'return\s+\[', method_body):
        return ' -> list:'
    # Check for boolean return
    if re.search(r'return\s+(True|False)\b', method_body):
        return ' -> bool:'
    # Check for integer return
    if re.search(r'return\s+\d+\b', method_body) or '.count()' in method_body:
        return ' -> int:'
    # Check for float return
    if re.search(r'return\s+float\(', method_body):
        return ' -> float:'
    # Check for string return
    if re.search(r'return\s+["\']', method_body) or 'str(' in method_body:
        return ' -> str:'
    # Default: assume it can return None (Optional type)
    return ' -> dict:'  # Most SerializerMethodFields return dict or None

def add_type_hints_to_file(filepath):
    """Add type hints to SerializerMethodField methods in a file"""
    full_path = BASE_DIR / filepath
    
    if not full_path.exists():
        print(f"⚠️  Skipping {filepath} (not found)")
        return 0
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match get_ methods without type hints
    pattern = r'(\n    def (get_\w+)\(self, obj\)):\n'
    
    matches = list(re.finditer(pattern, content))
    
    if not matches:
        print(f"✓ {filepath} (no methods to fix)")
        return 0
    
    # Process matches in reverse to maintain string positions
    modified_content = content
    changes = 0
    
    for match in reversed(matches):
        method_def = match.group(1)
        method_name = match.group(2)
        
        # Find the method body to analyze return type
        start_pos = match.end()
        # Simple heuristic: get next 500 chars to analyze
        method_sample = modified_content[start_pos:start_pos + 500]
        
        # Determine return type
        return_type = analyze_method_return_type(method_sample)
        
        # Replace method signature
        new_method_def = method_def + return_type
        modified_content = modified_content[:match.start()] + '\n    def ' + method_name + '(self, obj)' + return_type + '\n' + modified_content[match.end():]
        changes += 1
    
    if changes > 0:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        print(f"✓ {filepath} ({changes} methods fixed)")
    
    return changes

def main():
    print("=" * 60)
    print("🔧 Adding Type Hints to SerializerMethodField Methods")
    print("=" * 60)
    print()
    
    total_changes = 0
    
    for filepath in SERIALIZER_FILES:
        changes = add_type_hints_to_file(filepath)
        total_changes += changes
    
    print()
    print("=" * 60)
    print(f"✅ Complete! Total methods fixed: {total_changes}")
    print("=" * 60)

if __name__ == '__main__':
    main()
