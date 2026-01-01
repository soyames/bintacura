import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant

# Find the patient user
try:
    patient = Participant.objects.get(email='patient.test@vitacare.com')
    print(f"\n✅ Found patient:")
    print(f"   Email: {patient.email}")
    print(f"   Full Name: {patient.full_name}")
    print(f"   Phone: {patient.phone_number}")
    print(f"   UID: {patient.uid}")
    print(f"   Role: {patient.role}")
    
    # Check if full_name is empty
    if not patient.full_name or patient.full_name.strip() == '':
        print(f"\n⚠️  WARNING: Full name is empty!")
        print(f"   Setting full name to 'Test Patient'...")
        patient.full_name = 'Test Patient'
        patient.save()
        print(f"   ✅ Full name updated!")
    
except Participant.DoesNotExist:
    print(f"\n❌ Patient not found with email: patient.test@vitacare.com")
    
# Also check for the mysterious user
try:
    mystery_user = Participant.objects.get(email='amessinoukossi@gmail.com')
    print(f"\n⚠️  Found mystery user:")
    print(f"   Email: {mystery_user.email}")
    print(f"   Full Name: {mystery_user.full_name}")
    print(f"   Phone: {mystery_user.phone_number}")
    print(f"   UID: {mystery_user.uid}")
    print(f"   Role: {mystery_user.role}")
except Participant.DoesNotExist:
    print(f"\n✅ No mystery user found")
