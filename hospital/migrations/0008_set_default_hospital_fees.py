# Generated manually on 2024-12-30

from django.db import migrations
from django.conf import settings


def set_default_hospital_fees(apps, schema_editor):
    """
    Create HospitalData for existing hospitals and set default consultation fee.
    Uses DEFAULT_CONSULTATION_FEE_XOF from settings.
    """
    Participant = apps.get_model('core', 'Participant')
    HospitalData = apps.get_model('hospital', 'HospitalData')
    
    # Get default from settings, fallback to 3500 if not set
    default_fee_xof = getattr(settings, 'DEFAULT_CONSULTATION_FEE_XOF', 3500)
    
    # Get all hospital participants
    hospitals = Participant.objects.filter(role='hospital')
    
    created_count = 0
    for hospital in hospitals:
        # Create HospitalData if doesn't exist
        hospital_data, created = HospitalData.objects.get_or_create(
            participant=hospital,
            defaults={
                'license_number': f'HOSP{str(hospital.uid)[:8].upper()}',
                'consultation_fee': default_fee_xof,
                'bed_capacity': 0,
                'rating': 5.0,
            }
        )
        
        # Update consultation fee if it's 0
        if hospital_data.consultation_fee == 0:
            hospital_data.consultation_fee = default_fee_xof
            hospital_data.save()
            created_count += 1
    
    print(f"Created/Updated {created_count} hospital profiles with default consultation fee of {default_fee_xof} XOF")


def reverse_func(apps, schema_editor):
    """Reverse migration"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('hospital', '0007_hospitaldata'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(set_default_hospital_fees, reverse_func),
    ]
