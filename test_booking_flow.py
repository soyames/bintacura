#!/usr/bin/env python
"""
Test appointment booking flow
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant
from queue_management.services import QueueManagementService
from datetime import date, time

def test_appointment_booking():
    """Test the complete booking flow"""
    
    print("\n[TEST] APPOINTMENT BOOKING TEST")
    print("=" * 60)
    
    # 1. Get test participants
    print("\n[1] Finding test participants...")
    try:
        patient = Participant.objects.filter(role='patient').first()
        doctor = Participant.objects.filter(role='doctor').first()
        
        if not patient or not doctor:
            print("[X] No test participants found")
            return False
            
        print(f"[OK] Patient: {patient.full_name} ({patient.uid})")
        print(f"[OK] Doctor: {doctor.full_name} ({doctor.uid})")
    except Exception as e:
        print(f"[X] Error finding participants: {e}")
        return False
    
    # 2. Prepare appointment data
    print("\n[2] Preparing appointment data...")
    appointment_data = {
        'doctor': doctor,
        'appointment_date': date(2026, 1, 5),
        'appointment_time': time(10, 0),
        'type': 'consultation',
        'reason': 'Test booking',
        'symptoms': 'Test symptoms',
        'additional_services': []
    }
    print("[OK] Appointment data prepared")
    
    # 3. Test ONSITE payment (no wallet)
    print("\n[3] Testing ONSITE PAYMENT...")
    try:
        result = QueueManagementService.book_appointment_with_payment(
            patient=patient,
            appointment_data=appointment_data,
            payment_method='onsite_cash'
        )
        
        print(f"[OK] Appointment created: {result['appointment'].id}")
        print(f"   Queue number: {result['queue_number']}")
        print(f"   Payment status: {result['appointment'].payment_status}")
        print(f"   Payment method: {result['appointment'].payment_method}")
        print(f"   Total amount: {result['appointment'].final_price} {result['appointment'].currency}")
        
    except Exception as e:
        print(f"[X] Error with onsite payment: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. Test MOBILE MONEY payment
    print("\n[4] Testing MOBILE MONEY PAYMENT (FedaPay simulation)...")
    try:
        appointment_data['appointment_time'] = time(11, 0)
        result = QueueManagementService.book_appointment_with_payment(
            patient=patient,
            appointment_data=appointment_data,
            payment_method='mobile_money'
        )
        
        print(f"[OK] Appointment created: {result['appointment'].id}")
        print(f"   Queue number: {result['queue_number']}")
        print(f"   Payment status: {result['appointment'].payment_status}")
        print(f"   Payment method: {result['appointment'].payment_method}")
        
    except Exception as e:
        print(f"[X] Error with mobile money: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("[OK] ALL TESTS PASSED!")
    return True

if __name__ == '__main__':
    test_appointment_booking()
