import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant
from doctor.models import DoctorData, DoctorAffiliation
from hospital.models import HospitalData

print('=' * 70)
print('DOCTORS IN AWS DATABASE')
print('=' * 70)
doctors = Participant.objects.using("default").filter(role="doctor", is_active=True)
for doc in doctors:
    doc_data = DoctorData.objects.using("default").filter(participant=doc).first()
    print(f"Dr. {doc.first_name} {doc.last_name}")
    print(f"  UID: {doc.uid}")
    print(f"  Email: {doc.email}")
    print(f"  Phone: {doc.phone_number}")
    if doc_data:
        print(f"  Specialization: {doc_data.get_specialization_display()}")
        print(f"  License: {doc_data.license_number}")
        print(f"  Fee: {doc_data.consultation_fee} cents")
    print()

print('=' * 70)
print('HOSPITALS IN AWS DATABASE')
print('=' * 70)
hospitals = Participant.objects.using("default").filter(role="hospital", is_active=True)
for hosp in hospitals:
    hosp_data = HospitalData.objects.using("default").filter(participant=hosp).first()
    print(f"{hosp.first_name}")
    print(f"  UID: {hosp.uid}")
    print(f"  Email: {hosp.email}")
    print(f"  Phone: {hosp.phone_number}")
    if hosp_data:
        print(f"  Bed Capacity: {hosp_data.bed_capacity}")
        print(f"  License: {hosp_data.license_number}")
        print(f"  Consultation Fee: {hosp_data.get_consultation_fee()} cents")
        print(f"  Emergency: {hosp_data.emergency_services}")
        print(f"  ICU: {hosp_data.has_icu}")
    print()

print('=' * 70)
print('DOCTOR AFFILIATIONS')
print('=' * 70)
affiliations = DoctorAffiliation.objects.using("default").all()
print(f"Total affiliations: {affiliations.count()}")
for aff in affiliations[:5]:
    print(f"  Doctor: {aff.doctor.first_name} {aff.doctor.last_name} -> Hospital: {aff.hospital.first_name}")
print('=' * 70)
