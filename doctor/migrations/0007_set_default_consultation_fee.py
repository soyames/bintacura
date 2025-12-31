# Generated manually on 2024-12-30

from django.db import migrations
from django.conf import settings


def set_default_consultation_fees(apps, schema_editor):
    """
    Set default consultation fee for doctors who have 0 or null fee.
    Uses DEFAULT_CONSULTATION_FEE_XOF from settings.
    """
    DoctorData = apps.get_model('doctor', 'DoctorData')
    
    # Get default from settings, fallback to 3500 if not set
    default_fee_xof = getattr(settings, 'DEFAULT_CONSULTATION_FEE_XOF', 3500)
    
    # Update doctors with 0 or negative consultation fee
    updated_count = DoctorData.objects.filter(
        consultation_fee__lte=0
    ).update(consultation_fee=default_fee_xof)
    
    print(f"Updated {updated_count} doctor profiles with default consultation fee of {default_fee_xof} XOF")


def reverse_func(apps, schema_editor):
    """Reverse migration - set fees back to 0"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('doctor', '0006_remove_doctordata_affiliated_hospitals_and_more'),
    ]

    operations = [
        migrations.RunPython(set_default_consultation_fees, reverse_func),
    ]
