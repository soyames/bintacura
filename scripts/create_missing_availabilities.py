"""
Create missing availability slots for existing doctors and hospitals
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant
from appointments.signals import ensure_complete_availability
from django.conf import settings

print("\n" + "="*70)
print("CREATE MISSING AVAILABILITY SLOTS")
print("="*70 + "\n")

# Get all doctors and hospitals
doctors = Participant.objects.filter(role='doctor', is_active=True)
hospitals = Participant.objects.filter(role='hospital', is_active=True)

print(f"Found {doctors.count()} doctors and {hospitals.count()} hospitals\n")

total_created = 0

for doctor in doctors:
    created = ensure_complete_availability(doctor)
    if created:
        print(f"✓ Created {created} slots for Dr. {doctor.full_name}")
        total_created += created

for hospital in hospitals:
    created = ensure_complete_availability(hospital)
    if created:
        print(f"✓ Created {created} slots for {hospital.full_name}")
        total_created += created

print(f"\n{'='*70}")
print(f"Total availability slots created: {total_created}")
print(f"{'='*70}\n")
