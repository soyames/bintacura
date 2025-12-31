#!/usr/bin/env python
"""Check doctor consultation fees"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from doctor.models import DoctorData
from django.conf import settings

print(f"\nSettings DEFAULT_CONSULTATION_FEE_XOF: {settings.DEFAULT_CONSULTATION_FEE_XOF}")
print("\nChecking Doctor Consultation Fees:")
print("=" * 70)

docs = DoctorData.objects.all()[:10]
for d in docs:
    name = d.participant.full_name if d.participant else "No name"
    print(f"  {name}:")
    print(f"    - DB consultation_fee: {d.consultation_fee}")
    print(f"    - get_consultation_fee(): {d.get_consultation_fee()}")
    print()

print(f"\nTotal doctors: {DoctorData.objects.count()}")
print(f"Doctors with zero fee: {DoctorData.objects.filter(consultation_fee__lte=0).count()}")
print(f"Doctors with fee set: {DoctorData.objects.filter(consultation_fee__gt=0).count()}")
