"""
Script to add @extend_schema decorators to all APIView and ViewSet classes
to resolve DRF Spectacular warnings
"""

import re
import os

# Define view classes and their appropriate serializers
CORE_VIEWS_CONFIG = {
    'BeneficiariesAPIView': {
        'tag': 'Beneficiaries',
        'get': {'summary': 'List beneficiaries', 'response': 'DependentProfileSerializer'},
        'post': {'summary': 'Add beneficiary', 'request': 'DependentProfileSerializer', 'response': 'DependentProfileSerializer'}
    },
    'BeneficiaryDetailAPIView': {
        'tag': 'Beneficiaries',
        'get': {'summary': 'Get beneficiary details', 'response': 'DependentProfileSerializer'},
        'put': {'summary': 'Update beneficiary', 'request': 'DependentProfileSerializer', 'response': 'DependentProfileSerializer'},
        'delete': {'summary': 'Delete beneficiary', 'response': None}
    },
    'HospitalsAPIView': {
        'tag': 'Hospitals',
        'get': {'summary': 'List hospitals', 'response': 'HospitalProfileSerializer'}
    },
    'HospitalAppointmentsAPIView': {
        'tag': 'Hospital Appointments',
        'get': {'summary': 'List hospital appointments', 'response': 'ParticipantSerializer'}
    },
    'AvailableSlotsAPIView': {
        'tag': 'Appointments',
        'get': {'summary': 'Get available appointment slots', 'response': 'ParticipantSerializer'}
    },
    'PharmacyCatalogAPIView': {
        'tag': 'Pharmacy',
        'get': {'summary': 'Get pharmacy catalog', 'response': 'ParticipantSerializer'}
    },
    'PharmaciesAPIView': {
        'tag': 'Pharmacy',
        'get': {'summary': 'List pharmacies', 'response': 'ParticipantSerializer'}
    },
    'PharmacyOrdersAPIView': {
        'tag': 'Pharmacy Orders',
        'get': {'summary': 'List pharmacy orders', 'response': 'ParticipantSerializer'}
    },
    'AntiScrapingMonitorViewSet': {
        'tag': 'Security',
        'serializer_class': 'ParticipantSerializer'
    },
    'SecurityMonitorViewSet': {
        'tag': 'Security',
        'serializer_class': 'ParticipantSerializer'
    },
    'ContactFormAPIView': {
        'tag': 'Contact',
        'post': {'summary': 'Submit contact form', 'request': 'ParticipantSerializer', 'response': 'ParticipantSerializer'}
    },
}

def add_schema_to_view(file_path, view_name, config):
    """Add @extend_schema decorators to a view class"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # For ViewSet classes, add serializer_class
    if 'ViewSet' in view_name and 'serializer_class' in config:
        pattern = rf'(class {view_name}\([^)]+\):.*?(?:permission_classes = \[[^\]]+\])?)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            class_def = match.group(1)
            if 'serializer_class' not in class_def:
                replacement = f"{class_def}\n    serializer_class = {config['serializer_class']}"
                content = content.replace(class_def, replacement)
    
    # For APIView classes, add method decorators
    else:
        # Add class-level decorator
        pattern = rf'(class {view_name}\(APIView\):)'
        if re.search(pattern, content):
            tag = config.get('tag', 'API')
            replacement = f"@extend_schema(tags=['{tag}'])\n\\1"
            content = re.sub(pattern, replacement, content)
            
            # Add method-level decorators
            for method, method_config in config.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    # Build decorator
                    decorator_parts = [f"summary='{method_config['summary']}'"]
                    if 'request' in method_config:
                        decorator_parts.append(f"request={method_config['request']}")
                    if method_config.get('response'):
                        decorator_parts.append(f"responses={{200: {method_config['response']}}}")
                    
                    decorator = f"@extend_schema({', '.join(decorator_parts)})"
                    
                    # Find and replace method definition
                    method_pattern = rf'(    def {method}\(self, request[^)]*\):)'
                    if re.search(method_pattern, content):
                        content = re.sub(method_pattern, f"    {decorator}\n\\1", content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Updated {view_name}")

def main():
    """Main function to update all views"""
    core_views_path = r'C:\Users\soyam\Documents\GitHub\bintacura\core\views.py'
    
    print("Starting schema decorator updates...")
    print("=" * 60)
    
    for view_name, config in CORE_VIEWS_CONFIG.items():
        try:
            add_schema_to_view(core_views_path, view_name, config)
        except Exception as e:
            print(f"✗ Error updating {view_name}: {e}")
    
    print("=" * 60)
    print("Schema decorator updates complete!")

if __name__ == '__main__':
    main()
