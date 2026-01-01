import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from payments.fedapay_service import FedaPayService
from core.models import Participant

print("="*80)
print("FEDAPAY CUSTOMER CREATION DEBUG")
print("="*80)

# Get a test participant
try:
    participant = Participant.objects.filter(role='patient').first()
    
    if not participant:
        print("❌ No patient found in database")
        exit(1)
    
    print(f"\n📋 Participant Info:")
    print(f"   UID: {participant.uid}")
    print(f"   Full Name: {participant.full_name}")
    print(f"   Email: {participant.email}")
    print(f"   Phone: {participant.phone_number}")
    
    # Initialize FedaPay
    service = FedaPayService()
    
    # Format phone for display
    phone_data = service._format_phone_for_fedapay(participant.phone_number)
    print(f"\n📞 Formatted Phone for FedaPay:")
    print(f"   {json.dumps(phone_data, indent=2)}")
    
    # Prepare customer data
    name_parts = participant.full_name.split() if participant.full_name else ['User']
    firstname = name_parts[0]
    lastname = ' '.join(name_parts[1:]) if len(name_parts) > 1 else 'BINTACURA'
    
    customer_data = {
        'firstname': firstname,
        'lastname': lastname,
        'email': participant.email,
    }
    
    if phone_data:
        customer_data['phone_number'] = phone_data
    
    print(f"\n📤 Customer Data Being Sent:")
    print(json.dumps(customer_data, indent=2))
    
    # Try to create customer
    print(f"\n🚀 Creating FedaPay customer...")
    try:
        result = service.create_customer(participant)
        print(f"\n✅ Customer Created Successfully!")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"\n❌ Customer Creation Failed!")
        print(f"   Error: {str(e)}")
        
        # Check if it's a phone number issue
        print(f"\n🔍 Testing without phone number...")
        customer_data_no_phone = {
            'firstname': firstname,
            'lastname': lastname,
            'email': participant.email,
        }
        print(f"   Data: {json.dumps(customer_data_no_phone, indent=2)}")
        
        # Make direct request
        import requests
        url = f"{service.base_url}/customers"
        try:
            response = requests.post(url, headers=service.headers, json=customer_data_no_phone)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
        except Exception as e2:
            print(f"   Error: {str(e2)}")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
