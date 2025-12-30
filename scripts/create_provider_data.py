import os
import sys
import django

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Participant
from hospital.models import HospitalData
from django.conf import settings

def create_missing_provider_data():
    """Create missing HospitalData for existing hospitals"""
    
    print("\n" + "="*70)
    print("CREATE MISSING HOSPITAL DATA")
    print("="*70)
    
    # Get default consultation fee from settings
    default_fee = getattr(settings, 'DEFAULT_CONSULTATION_FEE_XOF', 3500)
    
    # Create HospitalData for hospitals without data
    hospitals = Participant.objects.filter(role='hospital', is_active=True)
    created_hospitals = 0
    
    for hospital in hospitals:
        if not hasattr(hospital, 'hospital_data') or hospital.hospital_data is None:
            HospitalData.objects.create(
                participant=hospital,
                license_number=f"HL-{hospital.country}-{str(hospital.uid)[:8].upper()}",
                bed_capacity=50,
                consultation_fee=default_fee,
                emergency_services=True,
                has_icu=True,
                has_maternity=True,
                has_laboratory=True,
                has_pharmacy=True,
                has_ambulance=True,
                specialties=["General Medicine", "Emergency Care"],
                operating_hours={"weekdays": "24/7", "weekends": "24/7"},
                rating=0,
                total_reviews=0
            )
            created_hospitals += 1
            print(f"  [CREATED] Hospital data for: {hospital.first_name}")
    
    print(f"\n" + "="*70)
    print(f"SUMMARY:")
    print(f"  Hospitals created: {created_hospitals}/{hospitals.count()}")
    print("="*70)

if __name__ == "__main__":
    create_missing_provider_data()
