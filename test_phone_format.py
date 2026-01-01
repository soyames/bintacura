import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from payments.fedapay_service import FedaPayService

# Test phone number formatting
service = FedaPayService()

test_numbers = [
    '+22997000001',
    '22997000002',
    '97000003',
    '+22661234567',  # Burkina Faso
    '+243123456789',  # DRC
    '+22512345678',  # Côte d'Ivoire (10 digits)
    '0097000004',
]

print("="*80)
print("PHONE NUMBER FORMATTING TEST")
print("="*80)

for num in test_numbers:
    result = service._format_phone_for_fedapay(num)
    print(f"\nInput:  {num}")
    print(f"Output: {result}")

print("\n" + "="*80)
