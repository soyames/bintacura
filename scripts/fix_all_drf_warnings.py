"""
Comprehensive script to add @extend_schema decorators to all remaining views
across different apps to eliminate DRF Spectacular warnings
"""

import os
import re

def add_import_if_missing(filepath):
    """Add drf_spectacular imports if not present"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'from drf_spectacular.utils import' in content:
        return content
    
    # Find rest_framework imports and add drf_spectacular after them
    pattern = r'(from rest_framework[^\n]+\n)'
    matches = list(re.finditer(pattern, content))
    
    if matches:
        last_match = matches[-1]
        insert_pos = last_match.end()
        new_import = 'from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter\n'
        content = content[:insert_pos] + new_import + content[insert_pos:]
    
    return content

def fix_hospital_views():
    """Fix hospital/views.py"""
    filepath = r'hospital\views.py'
    if not os.path.exists(filepath):
        print(f"✗ {filepath} not found")
        return
    
    content = add_import_if_missing(filepath)
    
    # Add decorator to HospitalAnalyticsViewSet
    content = re.sub(
        r'class HospitalAnalyticsViewSet\(viewsets\.ViewSet\):',
        '@extend_schema(tags=["Hospital Analytics"])\nclass HospitalAnalyticsViewSet(viewsets.ViewSet):',
        content
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {filepath}")

def fix_patient_views():
    """Fix patient/views.py"""
    filepath = r'patient\views.py'
    if not os.path.exists(filepath):
        print(f"✗ {filepath} not found")
        return
    
    content = add_import_if_missing(filepath)
    
    # Add decorator to PrescriptionsAPIView
    content = re.sub(
        r'class PrescriptionsAPIView\(APIView\):',
        '@extend_schema(tags=["Patient Prescriptions"])\nclass PrescriptionsAPIView(APIView):',
        content
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {filepath}")

def fix_pharmacy_cart_views():
    """Fix pharmacy/cart_views.py"""
    filepath = r'pharmacy\cart_views.py'
    if not os.path.exists(filepath):
        print(f"✗ {filepath} not found")
        return
    
    content = add_import_if_missing(filepath)
    
    # Add decorator to ShoppingCartViewSet
    content = re.sub(
        r'class ShoppingCartViewSet\(viewsets\.ViewSet\):',
        '@extend_schema(tags=["Shopping Cart"])\nclass ShoppingCartViewSet(viewsets.ViewSet):',
        content
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {filepath}")

def fix_pharmacy_views():
    """Fix pharmacy/views.py"""
    filepath = r'pharmacy\views.py'
    if not os.path.exists(filepath):
        print(f"✗ {filepath} not found")
        return
    
    content = add_import_if_missing(filepath)
    
    # Add decorators to function-based views
    content = re.sub(
        r'(@api_view\(\[\'POST\'\]\)[^\n]*\ndef prepare_prescription)',
        r'@extend_schema(tags=["Pharmacy"], summary="Prepare prescription")\n\1',
        content
    )
    
    content = re.sub(
        r'(@api_view\(\[\'GET\'\]\)[^\n]*\ndef search_prescription)',
        r'@extend_schema(tags=["Pharmacy"], summary="Search prescription")\n\1',
        content
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {filepath}")

def fix_qrcode_views():
    """Fix qrcode_generator/views.py"""
    filepath = r'qrcode_generator\views.py'
    if not os.path.exists(filepath):
        print(f"✗ {filepath} not found")
        return
    
    content = add_import_if_missing(filepath)
    
    # Add decorators to QR code views
    content = re.sub(
        r'class GenerateQRCodeView\(APIView\):',
        '@extend_schema(tags=["QR Code"])\nclass GenerateQRCodeView(APIView):',
        content
    )
    
    content = re.sub(
        r'class GetQRCodeView\(APIView\):',
        '@extend_schema(tags=["QR Code"])\nclass GetQRCodeView(APIView):',
        content
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {filepath}")

def fix_queue_management_views():
    """Fix queue_management/views.py"""
    filepath = r'queue_management\views.py'
    if not os.path.exists(filepath):
        print(f"✗ {filepath} not found")
        return
    
    content = add_import_if_missing(filepath)
    
    # Add decorators to function-based views
    function_views = [
        ('BookAppointmentWithQueueView', 'Book appointment with queue'),
        ('call_next_patient', 'Call next patient'),
        ('complete_appointment_with_queue', 'Complete appointment'),
        ('get_my_queue_position', 'Get queue position'),
        ('get_queue_status', 'Get queue status'),
    ]
    
    for view_name, summary in function_views:
        if 'View' in view_name:
            # Class-based view
            content = re.sub(
                rf'class {view_name}\(APIView\):',
                f'@extend_schema(tags=["Queue Management"], summary="{summary}")\nclass {view_name}(APIView):',
                content
            )
        else:
            # Function-based view
            content = re.sub(
                rf'(@api_view\([^\)]+\)[^\n]*\ndef {view_name})',
                f'@extend_schema(tags=["Queue Management"], summary="{summary}")\n\\1',
                content
            )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {filepath}")

def main():
    print("=" * 70)
    print("FIXING DRF SPECTACULAR WARNINGS - COMPREHENSIVE APPROACH")
    print("=" * 70)
    print()
    
    fix_hospital_views()
    fix_patient_views()
    fix_pharmacy_cart_views()
    fix_pharmacy_views()
    fix_qrcode_views()
    fix_queue_management_views()
    
    print()
    print("=" * 70)
    print("ALL FIXES APPLIED")
    print("=" * 70)

if __name__ == '__main__':
    main()
