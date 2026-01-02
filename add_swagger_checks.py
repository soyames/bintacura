"""
Script to add swagger_fake_view checks to all ViewSets with queryset issues
Fixes DRF Spectacular W001 warnings for AnonymousUser errors
"""

import re
from pathlib import Path

BASE_DIR = Path(r'C:\Users\soyam\Documents\GitHub\bintacura')

# Files to process based on warnings
VIEWSET_FILES = [
    'health_records/views.py',
    'hospital/views.py',
    'patient/views.py',
    'insurance/views.py',
    'pharmacy/views.py',
]

def add_swagger_check_to_get_queryset(filepath):
    """Add swagger_fake_view check to get_queryset methods"""
    full_path = BASE_DIR / filepath
    
    if not full_path.exists():
        print(f"⚠️  Skipping {filepath} (not found)")
        return 0
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match get_queryset methods that don't have swagger_fake_view check
    # and access request.user
    pattern = r'(    def get_queryset\(self\):.*?\n)(        (?!if getattr\(self, .swagger_fake_view))'
    
    # Find all get_queryset methods
    matches = list(re.finditer(r'    def get_queryset\(self\):[^\n]*\n(.*?)(?=\n    def |\nclass |\Z)', content, re.DOTALL))
    
    if not matches:
        print(f"✓ {filepath} (no get_queryset methods)")
        return 0
    
    modified_content = content
    changes = 0
    
    #Process matches in reverse to maintain string positions
    for match in reversed(matches):
        method_body = match.group(1)
        
        # Skip if already has swagger_fake_view check
        if 'swagger_fake_view' in method_body:
            continue
        
        # Skip if doesn't access request.user (likely safe)
        if 'request.user' not in method_body and 'self.request.user' not in method_body:
            continue
        
        # Find the correct model name from the method body
        # Look for Model.objects patterns
        model_match = re.search(r'(\w+)\.objects', method_body)
        if not model_match:
            continue
        
        model_name = model_match.group(1)
        
        # Get the method signature line
        method_start = match.start()
        method_sig_end = content.find('\n', method_start) + 1
        
        # Find the first line of actual code (skip comments and docstrings)
        first_code_line_match = re.search(r'\n        [^"\'\s#]', content[method_sig_end:method_sig_end + 500])
        if not first_code_line_match:
            continue
        
        insert_pos = method_sig_end + first_code_line_match.start() + 1
        
        # Insert the swagger check
        swagger_check = f"        if getattr(self, 'swagger_fake_view', False):\n            return {model_name}.objects.none()\n"
        
        modified_content = modified_content[:insert_pos] + swagger_check + modified_content[insert_pos:]
        changes += 1
    
    if changes > 0:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        print(f"✓ {filepath} ({changes} methods fixed)")
    else:
        print(f"✓ {filepath} (already fixed or no changes needed)")
    
    return changes

def main():
    print("=" * 60)
    print("🔧 Adding swagger_fake_view Checks to ViewSets")
    print("=" * 60)
    print()
    
    total_changes = 0
    
    for filepath in VIEWSET_FILES:
        changes = add_swagger_check_to_get_queryset(filepath)
        total_changes += changes
    
    print()
    print("=" * 60)
    print(f"✅ Complete! Total methods fixed: {total_changes}")
    print("=" * 60)

if __name__ == '__main__':
    main()
