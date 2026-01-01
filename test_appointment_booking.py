"""
Test appointment booking to identify remaining issues
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant
from appointments.models import Appointment, AppointmentQueue
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from queue_management.views import BookAppointmentWithQueueView
import json

print("\n" + "="*80)
print("🔍 TESTING APPOINTMENT BOOKING SYSTEM")
print("="*80 + "\n")

# Get test users
User = get_user_model()

try:
    patient = User.objects.filter(role='patient').first()
    doctor = User.objects.filter(role='doctor').first()
    
    if not patient:
        print("❌ No patient found in database")
        exit(1)
    
    if not doctor:
        print("❌ No doctor found in database")
        exit(1)
    
    print(f"✅ Test Patient: {patient.full_name} ({patient.email})")
    print(f"✅ Test Doctor: {doctor.full_name} ({doctor.email})")
    print()
    
    # Test 1: Cash Payment
    print("📋 TEST 1: Cash Payment (Onsite)")
    print("-" * 80)
    
    factory = APIRequestFactory()
    request = factory.post('/api/v1/queue/book-appointment/', {
        'participant_id': str(doctor.uid),
        'appointment_date': '2026-01-05',
        'appointment_time': '10:00',
        'type': 'consultation',
        'reason': 'Test checkup - Cash',
        'payment_method': 'onsite'
    }, format='json')
    request.user = patient
    
    view = BookAppointmentWithQueueView.as_view()
    
    try:
        response = view(request)
        print(f"   Status: {response.status_code}")
        if response.status_code == 201:
            print(f"   ✅ SUCCESS")
            print(f"   Data: {json.dumps(response.data, indent=2)}")
            
            # Check if appointment was created
            appointment_id = response.data.get('appointment_id')
            if appointment_id:
                appt = Appointment.objects.get(id=appointment_id)
                print(f"\n   📋 Appointment Details:")
                print(f"      - ID: {appt.id}")
                print(f"      - Status: {appt.status}")
                print(f"      - Payment Status: {appt.payment_status}")
                print(f"      - Payment Method: {appt.payment_method}")
                print(f"      - Patient: {appt.patient.full_name}")
                print(f"      - Doctor: {appt.doctor.full_name if appt.doctor else 'N/A'}")
                print(f"      - Date: {appt.appointment_date}")
                print(f"      - Queue Number: {appt.queue_number}")
        else:
            print(f"   ❌ FAILED")
            print(f"   Error: {response.data}")
    except Exception as e:
        print(f"   ❌ ERROR: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Test 2: Online Payment
    print("📋 TEST 2: Online Payment")
    print("-" * 80)
    
    request2 = factory.post('/api/v1/queue/book-appointment/', {
        'participant_id': str(doctor.uid),
        'appointment_date': '2026-01-06',
        'appointment_time': '14:00',
        'type': 'consultation',
        'reason': 'Test checkup - Online',
        'payment_method': 'online'
    }, format='json')
    request2.user = patient
    
    try:
        response2 = view(request2)
        print(f"   Status: {response2.status_code}")
        if response2.status_code == 201:
            print(f"   ✅ SUCCESS")
            print(f"   Data: {json.dumps(response2.data, indent=2)}")
        else:
            print(f"   ❌ FAILED")
            print(f"   Error: {response2.data}")
    except Exception as e:
        print(f"   ❌ ERROR: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Test 3: Check all appointments for patient
    print("📋 TEST 3: Checking Patient's Appointments")
    print("-" * 80)
    
    appointments = Appointment.objects.filter(patient=patient).order_by('-created_at')[:5]
    print(f"   Total appointments: {appointments.count()}")
    
    for idx, appt in enumerate(appointments, 1):
        print(f"\n   {idx}. Appointment {appt.id}")
        print(f"      - Status: {appt.status}")
        print(f"      - Payment: {appt.payment_status} ({appt.payment_method})")
        print(f"      - Date: {appt.appointment_date} {appt.appointment_time}")
        print(f"      - Doctor: {appt.doctor.full_name if appt.doctor else 'N/A'}")
        print(f"      - Queue: {appt.queue_number}")
    
    print()
    
    # Test 4: Check visible appointments (what shows on page)
    print("📋 TEST 4: Checking Visible Appointments (from view query)")
    print("-" * 80)
    
    from datetime import date
    visible_appointments = Appointment.objects.filter(
        patient=patient,
        status__in=["pending", "confirmed", "in_progress"],
        appointment_date__gte=date.today(),
    ).order_by("appointment_date", "appointment_time")
    
    print(f"   Visible (upcoming) appointments: {visible_appointments.count()}")
    
    for idx, appt in enumerate(visible_appointments, 1):
        print(f"\n   {idx}. Appointment {appt.id}")
        print(f"      - Status: {appt.status}")
        print(f"      - Payment: {appt.payment_status}")
        print(f"      - Date: {appt.appointment_date} {appt.appointment_time}")
    
    print()
    print("="*80)
    print("✅ TEST COMPLETE")
    print("="*80)
    
except Exception as e:
    print(f"\n❌ FATAL ERROR: {type(e).__name__}")
    print(f"   Message: {str(e)}")
    import traceback
    traceback.print_exc()
