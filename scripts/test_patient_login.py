#!/usr/bin/env python
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
django.setup()

from core.models import Participant
from doctor.models import DoctorData

# Check if smartwork608@gmail.com exists and is active
patient = Participant.objects.filter(email='smartwork608@gmail.com').first()
if patient:
    print(f'✓ Patient found: {patient.email}')
    print(f'  - Role: {patient.role}')
    print(f'  - Active: {patient.is_active}')
    print(f'  - Email verified: {patient.is_email_verified}')
else:
    print('✗ Patient not found')

# Check doctors
doctors = Participant.objects.filter(role='doctor', is_active=True)
print(f'\n✓ Found {doctors.count()} active doctors')

for doc in doctors[:5]:
    doc_data = getattr(doc, 'doctor_data', None)
    if doc_data:
        fee = doc_data.get_consultation_fee()
        print(f'  - {doc.get_full_name()}: {doc_data.specialization} - Fee: {fee} XOF')
    else:
        print(f'  - {doc.get_full_name()}: NO doctor_data')
