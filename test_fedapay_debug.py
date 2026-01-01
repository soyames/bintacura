"""
FedaPay Debug Script - Test API requests
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings
import requests
import json

print("="*80)
print("🔧 FEDAPAY DEBUG SCRIPT")
print("="*80)
print()

# 1. Check environment variables
print("📋 Step 1: Checking FedaPay Configuration")
print("-" * 80)
print(f"Environment: {settings.FEDAPAY_ENVIRONMENT}")
print(f"Secret Key: {'✅ Set' if settings.FEDAPAY_API_KEY else '❌ Not Set'}")
print(f"Webhook Secret: {'✅ Set' if settings.FEDAPAY_WEBHOOK_SECRET else '❌ Not Set'}")
print(f"API Key Length: {len(settings.FEDAPAY_API_KEY) if settings.FEDAPAY_API_KEY else 0}")
print()

# Get current keys based on environment
api_key = settings.FEDAPAY_API_KEY
if settings.FEDAPAY_ENVIRONMENT == 'sandbox':
    base_url = 'https://sandbox-api.fedapay.com/v1'
else:
    base_url = 'https://api.fedapay.com/v1'

print(f"Current API Base URL: {base_url}")
print(f"API Key Length: {len(api_key) if api_key else 0}")
print()

# 2. Test customer creation
print("📋 Step 2: Testing Customer Creation")
print("-" * 80)

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

customer_data = {
    "firstname": "John",
    "lastname": "Doe",
    "email": f"john.doe.{os.urandom(4).hex()}@example.com",  # Random email to avoid duplicates
    "phone_number": {
        "number": "97000001",  # NO + or country code, just 8 digits
        "country": "BJ"
    }
}

print(f"Request URL: {base_url}/customers")
print(f"Request Headers: {json.dumps({k: v[:20] + '...' if k == 'Authorization' else v for k, v in headers.items()}, indent=2)}")
print(f"Request Data: {json.dumps(customer_data, indent=2)}")
print()

try:
    response = requests.post(
        f"{base_url}/customers",
        headers=headers,
        json=customer_data,
        timeout=30
    )
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()
    print(f"Response Body:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print()
    
    if response.status_code in [200, 201]:
        print("✅ Customer creation successful!")
        customer_response = response.json()
        customer_info = customer_response.get('v1/customer', customer_response)
        customer_id = customer_info.get('id')
        print(f"Customer ID: {customer_id}")
    else:
        print("❌ Customer creation failed!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()

# 3. Test transaction creation
print("📋 Step 3: Testing Transaction Creation")
print("-" * 80)

transaction_data = {
    "description": "Test appointment payment",
    "amount": 5000,  # 5000 XOF
    "currency": {
        "iso": "XOF"
    },
    "callback_url": "http://127.0.0.1:8080/api/v1/payments/fedapay/webhook/",
    "customer": {
        "firstname": "Jane",
        "lastname": "Smith",
        "email": f"jane.smith.{os.urandom(4).hex()}@example.com",
        "phone_number": {
            "number": "97000002",  # NO + or country code, just 8 digits
            "country": "BJ"
        }
    }
}

print(f"Request URL: {base_url}/transactions")
print(f"Request Data: {json.dumps(transaction_data, indent=2)}")
print()

try:
    response = requests.post(
        f"{base_url}/transactions",
        headers=headers,
        json=transaction_data,
        timeout=30
    )
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Body:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print()
    
    if response.status_code in [200, 201]:
        print("✅ Transaction creation successful!")
        transaction_response = response.json()
        transaction_info = transaction_response.get('v1/transaction', transaction_response)
        print(f"Transaction ID: {transaction_info.get('id')}")
        print(f"Transaction Reference: {transaction_info.get('reference')}")
        print(f"Transaction Status: {transaction_info.get('status')}")
        print(f"Payment URL: {transaction_info.get('payment_url')}")
    else:
        print("❌ Transaction creation failed!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*80)
print("✅ FedaPay Debug Complete")
print("="*80)
