import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from doctor.models import DoctorData
from doctor.serializers import DoctorDataSerializer
from core.models import Participant
import traceback

print("\n=== Testing Doctor API ===\n")

try:
    # Check for doctors in database
    doctors = Participant.objects.filter(role='doctor', is_active=True)
    print(f"Total active doctors: {doctors.count()}")
    
    if doctors.exists():
        print("\nDoctors found:")
        for doc in doctors[:5]:
            print(f"  - {doc.first_name} {doc.last_name} (UID: {doc.uid})")
            try:
                doc_data = DoctorData.objects.get(participant=doc)
                print(f"    Specialization: {doc_data.specialization}")
                print(f"    Consultation Fee: {doc_data.consultation_fee} XOF")
            except DoctorData.DoesNotExist:
                print(f"    ⚠️ No DoctorData record found")
    
    # Test serializer
    print("\n=== Testing Serializer ===")
    doctor_data_qs = DoctorData.objects.select_related("participant").filter(
        participant__is_active=True
    )
    print(f"DoctorData records found: {doctor_data_qs.count()}")
    
    if doctor_data_qs.exists():
        serializer = DoctorDataSerializer(doctor_data_qs, many=True)
        data = serializer.data
        print(f"✓ Serialization successful - {len(data)} doctors serialized")
        if data:
            print(f"\nFirst doctor data:")
            print(f"  Name: {data[0].get('first_name')} {data[0].get('last_name')}")
            print(f"  Specialization: {data[0].get('specialization')}")
    else:
        print("⚠️ No DoctorData records found in database")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    traceback.print_exc()

print("\n=== Test Complete ===\n")
