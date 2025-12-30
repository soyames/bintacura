import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant
from doctor.models import DoctorData
from hospital.models import HospitalData

print('=' * 70)
print('AWS DATABASE STATUS')
print('=' * 70)
print(f'Participants: {Participant.objects.using("default").count()}')
print(f'  - Doctors: {Participant.objects.using("default").filter(role="doctor").count()}')
print(f'  - Hospitals: {Participant.objects.using("default").filter(role="hospital").count()}')
print(f'  - Patients: {Participant.objects.using("default").filter(role="patient").count()}')
print(f'DoctorData: {DoctorData.objects.using("default").count()}')
print(f'HospitalData: {HospitalData.objects.using("default").count()}')

print()
print('=' * 70)
print('RENDER DATABASE STATUS')
print('=' * 70)
print(f'Participants: {Participant.objects.using("frankfurt").count()}')
print(f'  - Doctors: {Participant.objects.using("frankfurt").filter(role="doctor").count()}')
print(f'  - Hospitals: {Participant.objects.using("frankfurt").filter(role="hospital").count()}')
print(f'  - Patients: {Participant.objects.using("frankfurt").filter(role="patient").count()}')
print(f'DoctorData: {DoctorData.objects.using("frankfurt").count()}')
print(f'HospitalData: {HospitalData.objects.using("frankfurt").count()}')
print('=' * 70)
