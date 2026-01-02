import re

# Read core/views.py
with open('core/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add decorators for remaining APIView classes
replacements = [
    # HospitalAppointmentsAPIView
    (r'class HospitalAppointmentsAPIView\(APIView\):', 
     '@extend_schema(tags=["Hospital Appointments"])\nclass HospitalAppointmentsAPIView(APIView):'),
    
    # AvailableSlotsAPIView  
    (r'class AvailableSlotsAPIView\(APIView\):', 
     '@extend_schema(tags=["Appointments"])\nclass AvailableSlotsAPIView(APIView):'),
    
    # PharmacyCatalogAPIView
    (r'class PharmacyCatalogAPIView\(APIView\):', 
     '@extend_schema(tags=["Pharmacy"])\nclass PharmacyCatalogAPIView(APIView):'),
    
    # PharmaciesAPIView
    (r'class PharmaciesAPIView\(APIView\):', 
     '@extend_schema(tags=["Pharmacy"])\nclass PharmaciesAPIView(APIView):'),
    
    # PharmacyOrdersAPIView
    (r'class PharmacyOrdersAPIView\(APIView\):', 
     '@extend_schema(tags=["Pharmacy Orders"])\nclass PharmacyOrdersAPIView(APIView):'),
    
    # ContactFormAPIView
    (r'class ContactFormAPIView\(APIView\):', 
     '@extend_schema(tags=["Contact"])\nclass ContactFormAPIView(APIView):'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Write back
with open('core/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✓ Added class-level decorators to remaining APIViews')
