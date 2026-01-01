#!/usr/bin/env python
"""
Test FedaPay API configuration and connection
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings
import base64
import requests

print("="*70)
print("🔍 FEDAPAY CONFIGURATION TEST")
print("="*70)
print()

# Check environment variables
print("📋 Environment Variables:")
print(f"  FEDAPAY_API_KEY: {'✅ Set' if settings.FEDAPAY_API_KEY else '❌ Not Set'}")
if settings.FEDAPAY_API_KEY:
    print(f"    Length: {len(settings.FEDAPAY_API_KEY)} characters")
    print(f"    Starts with: {settings.FEDAPAY_API_KEY[:8]}...")
print(f"  FEDAPAY_ENVIRONMENT: {settings.FEDAPAY_ENVIRONMENT}")
print()

if not settings.FEDAPAY_API_KEY:
    print("❌ ERROR: FEDAPAY_API_KEY is not configured!")
    print("   Please add it to your .env file:")
    print("   FEDAPAY_API_KEY=sk_sandbox_your_key_here")
    sys.exit(1)

# Test API connection
print("🔌 Testing FedaPay API Connection...")
print()

api_key = settings.FEDAPAY_API_KEY
environment = getattr(settings, 'FEDAPAY_ENVIRONMENT', 'sandbox')

if environment == 'sandbox':
    base_url = 'https://sandbox-api.fedapay.com/v1'
else:
    base_url = 'https://api.fedapay.com/v1'

# Create Basic Auth header
credentials = f"{api_key}:".encode('utf-8')
encoded_credentials = base64.b64encode(credentials).decode('utf-8')

headers = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
}

try:
    # Test with a simple API call (get account info)
    response = requests.get(f'{base_url}/account', headers=headers)
    
    print(f"  Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("  ✅ SUCCESS: FedaPay API connection successful!")
        data = response.json()
        if 'v1/account' in data:
            account = data['v1/account']
            print(f"  Account ID: {account.get('id', 'N/A')}")
            print(f"  Name: {account.get('name', 'N/A')}")
            print(f"  Status: {account.get('status', 'N/A')}")
    elif response.status_code == 401:
        print("  ❌ AUTHENTICATION FAILED!")
        print("  Possible issues:")
        print("    1. API key is invalid")
        print("    2. Using sandbox key with live environment (or vice versa)")
        print("    3. API key has been revoked")
        print()
        print(f"  Response: {response.text}")
    else:
        print(f"  ⚠️  Unexpected response: {response.status_code}")
        print(f"  Response: {response.text}")
        
except Exception as e:
    print(f"  ❌ ERROR: {str(e)}")

print()
print("="*70)
print("💡 TIP: Get your FedaPay API key from:")
print("   https://dashboard.fedapay.com/developers/api-keys")
print("="*70)
