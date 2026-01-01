"""
Test FedaPay Full Payment Flow
This script tests the complete payment flow from customer creation to token generation
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from payments.fedapay_service import FedaPayService
from core.models import Participant
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_full_payment_flow():
    """Test the complete payment flow"""
    
    print("\n" + "="*80)
    print("🧪 TESTING FEDAPAY FULL PAYMENT FLOW")
    print("="*80 + "\n")
    
    # Get the logged-in patient
    try:
        patient = Participant.objects.get(email='patient.test@vitacare.com')
        print(f"✅ Found patient: {patient.full_name} ({patient.email})")
        print(f"   Phone: {patient.phone_number}")
    except Participant.DoesNotExist:
        print("❌ Patient not found!")
        return
    
    fedapay_service = FedaPayService()
    
    # Step 1: Create Customer
    print("\n" + "-"*80)
    print("Step 1: Creating FedaPay Customer")
    print("-"*80)
    
    try:
        customer = fedapay_service.create_customer(patient)
        print(f"✅ Customer created:")
        print(f"   ID: {customer.get('id')}")
        print(f"   Name: {customer.get('firstname')} {customer.get('lastname')}")
        print(f"   Email: {customer.get('email')}")
    except Exception as e:
        print(f"❌ Customer creation failed: {str(e)}")
        return
    
    # Step 2: Create Transaction
    print("\n" + "-"*80)
    print("Step 2: Creating Transaction")
    print("-"*80)
    
    try:
        transaction = fedapay_service.create_transaction(
            amount=3500,  # 3500 XOF
            currency='XOF',
            description='Test appointment payment',
            customer_id=customer['id'],
            callback_url='http://127.0.0.1:8080/api/v1/payments/fedapay/webhook/',
            custom_metadata={
                'appointment_id': 'test-123',
                'patient_email': patient.email
            }
        )
        
        print(f"✅ Transaction created:")
        print(f"   ID: {transaction.get('id')}")
        print(f"   Reference: {transaction.get('reference')}")
        print(f"   Amount: {transaction.get('amount')} XOF")
        print(f"   Status: {transaction.get('status')}")
    except Exception as e:
        print(f"❌ Transaction creation failed: {str(e)}")
        return
    
    # Step 3: Generate Payment Token
    print("\n" + "-"*80)
    print("Step 3: Generating Payment Token")
    print("-"*80)
    
    try:
        token_data = fedapay_service.generate_payment_token(transaction['id'])
        
        print(f"✅ Payment token generated:")
        print(f"   Token: {token_data.get('token', '')[:50]}...")
        print(f"   Payment URL: {token_data.get('url', '')}")
        
        print("\n" + "="*80)
        print("🎉 FULL FLOW TEST COMPLETE!")
        print("="*80)
        print(f"\n💳 Payment URL: {token_data.get('url', '')}")
        print("\nYou can use this URL to complete the payment in FedaPay sandbox.")
        
    except Exception as e:
        print(f"❌ Token generation failed: {str(e)}")
        return

if __name__ == '__main__':
    test_full_payment_flow()
