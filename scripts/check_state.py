import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from doctor.models import DoctorData
from hospital.models import HospitalData
from core.models import Participant

print('=== CURRENT STATE ===')
print(f'Total Participants: {Participant.objects.count()}')
print(f'  - Patients: {Participant.objects.filter(role="patient").count()}')
print(f'  - Doctors: {Participant.objects.filter(role="doctor").count()}')
print(f'  - Hospitals: {Participant.objects.filter(role="hospital").count()}')
print(f'  - Pharmacies: {Participant.objects.filter(role="pharmacy").count()}')
print(f'  - Insurance: {Participant.objects.filter(role="insurance").count()}')

print('\n=== DOCTOR FEES ===')
for doctor in DoctorData.objects.all()[:5]:
    print(f'  {doctor.participant.get_full_name()}: {doctor.consultation_fee} XOF')

print('\n=== HOSPITAL FEES ===')
for hospital in HospitalData.objects.all()[:5]:
    print(f'  {hospital.participant.get_full_name()}: {hospital.consultation_fee} XOF')
