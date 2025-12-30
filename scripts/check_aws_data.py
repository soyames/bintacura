import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Participant
from doctor.models import DoctorProfile
from hospital.models import HospitalProfile

print("\n" + "="*70)
print("AWS DATABASE DATA CHECK")
print("="*70)

aws_participants = Participant.objects.using('default').count()
aws_doctors = DoctorProfile.objects.using('default').count()
aws_hospitals = HospitalProfile.objects.using('default').count()

print(f"\nAWS Database (default):")
print(f"  Participants: {aws_participants}")
print(f"  Doctors: {aws_doctors}")
print(f"  Hospitals: {aws_hospitals}")

if aws_participants > 0:
    print(f"\nSample participants:")
    for p in Participant.objects.using('default')[:5]:
        print(f"  - {p.email} ({p.role}) - Active: {p.is_active}")

print("="*70 + "\n")
