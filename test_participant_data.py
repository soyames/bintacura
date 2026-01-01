"""
Test script to verify participant data extraction for FedaPay
Run with: python test_participant_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant

print("\n" + "="*80)
print("TESTING PARTICIPANT DATA EXTRACTION")
print("="*80 + "\n")

# Get the test patient
try:
    patient = Participant.objects.get(email="patient.test@vitacare.com")
    
    print(f"✅ Found participant:")
    print(f"   Email: {patient.email}")
    print(f"   Full Name: {patient.full_name}")
    print(f"   Phone: {patient.phone_number}")
    print(f"   Role: {patient.role}")
    print(f"   UID: {patient.uid}")
    
    # Test name splitting
    name_parts = patient.full_name.split() if patient.full_name else ['User']
    firstname = name_parts[0] if name_parts else 'User'
    lastname = ' '.join(name_parts[1:]) if len(name_parts) > 1 else 'BINTACURA'
    
    print(f"\n📋 Name split for FedaPay:")
    print(f"   First Name: {firstname}")
    print(f"   Last Name: {lastname}")
    
    # Test phone formatting
    from payments.fedapay_service import FedaPayService
    fedapay = FedaPayService()
    phone_data = fedapay._format_phone_for_fedapay(patient.phone_number)
    
    print(f"\n📱 Phone formatted for FedaPay:")
    if phone_data:
        print(f"   Number: {phone_data['number']}")
        print(f"   Country: {phone_data['country']}")
    else:
        print(f"   ❌ Phone formatting failed!")
    
    # Show what would be sent to FedaPay
    print(f"\n🔵 Data that would be sent to FedaPay:")
    print(f"   {{")
    print(f"     'firstname': '{firstname}',")
    print(f"     'lastname': '{lastname}',")
    print(f"     'email': '{patient.email}',")
    if phone_data:
        print(f"     'phone_number': {phone_data}")
    print(f"   }}")
    
    print(f"\n✅ All participant data looks correct!")
    
except Participant.DoesNotExist:
    print(f"❌ Patient with email 'patient.test@vitacare.com' not found!")
    print(f"   Please create a test patient account first.")
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
