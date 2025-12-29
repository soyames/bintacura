import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bintacura_backend.settings')
django.setup()

from core.models import Participant
from appointments.models import Availability
from appointments.utils import create_default_availability_slots


def generate_default_slots():
    """Generate default 30-minute slots for all hospitals and doctors (24/7) - only for missing days"""
    
    doctors_and_hospitals = Participant.objects.filter(
        role__in=['doctor', 'hospital'],
        is_active=True
    )
    
    print(f"\nFound {doctors_and_hospitals.count()} doctors and hospitals")
    
    total_created = 0
    total_skipped = 0
    
    for participant in doctors_and_hospitals:
        existing_count = Availability.objects.filter(participant=participant).count()
        
        if existing_count > 0:
            print(f"⚠ Skipping {participant.name} - already has {existing_count} slots configured")
            total_skipped += 1
            continue
        
        before_count = Availability.objects.filter(participant=participant).count()
        create_default_availability_slots(participant)
        after_count = Availability.objects.filter(participant=participant).count()
        created_count = after_count - before_count
        
        total_created += created_count
        print(f"✓ Created {created_count} slots for {participant.name} ({participant.role})")
    
    print(f"\n✓ Created {total_created} new availability slots")
    print(f"⚠ Skipped {total_skipped} participants with existing slots")
    print(f"✓ All doctors and hospitals now have availability configured")


if __name__ == '__main__':
    print("="*80)
    print("GENERATING DEFAULT AVAILABILITY SLOTS")
    print("="*80)
    generate_default_slots()
    print("="*80)

