# Generated migration for DoctorService to ParticipantService conversion

from django.db import migrations, models
from decimal import Decimal


def migrate_doctor_services_to_participant_services(apps, schema_editor):
    """
    Migrate all DoctorService records to ParticipantService.
    Converts price from cents (IntegerField) to major units (DecimalField).
    Maps doctor field to participant field.
    Adds currency='XOF' to all records.
    """
    DoctorService = apps.get_model('doctor', 'DoctorService')
    ParticipantService = apps.get_model('core', 'ParticipantService')
    
    migrated_count = 0
    skipped_count = 0
    
    for doctor_service in DoctorService.objects.all():
        # Check if this service was already migrated
        existing = ParticipantService.objects.filter(
            participant=doctor_service.doctor,
            name=doctor_service.name,
            category=doctor_service.category
        ).first()
        
        if existing:
            skipped_count += 1
            continue
        
        # Convert price from cents to major units
        # DoctorService.price is in cents, ParticipantService.price is in XOF
        price_in_major_units = Decimal(doctor_service.price) / Decimal(100)
        
        # Create new ParticipantService
        ParticipantService.objects.create(
            participant=doctor_service.doctor,  # Map doctor -> participant
            name=doctor_service.name,
            category=doctor_service.category,
            description=doctor_service.description or '',
            price=price_in_major_units,
            currency='XOF',
            duration_minutes=doctor_service.duration_minutes,
            is_active=doctor_service.is_active,
            is_available=doctor_service.is_available,
            region_code=doctor_service.region_code,
            created_at=doctor_service.created_at,
            updated_at=doctor_service.updated_at,
            synced=doctor_service.synced
        )
        
        migrated_count += 1
    
    print(f"✅ Migrated {migrated_count} DoctorService records to ParticipantService")
    print(f"⏭️  Skipped {skipped_count} records (already exist)")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration - delete ParticipantService records that came from DoctorService.
    Only deletes services for participants with role='doctor' and matching categories.
    """
    ParticipantService = apps.get_model('core', 'ParticipantService')
    
    # Categories that exist in DoctorService
    doctor_categories = ['consultation', 'diagnostic', 'therapy', 'vaccination', 'other']
    
    deleted = ParticipantService.objects.filter(
        participant__role='doctor',
        category__in=doctor_categories
    ).delete()
    
    print(f"⏪ Reverse migration: Deleted {deleted[0]} ParticipantService records")


class Migration(migrations.Migration):

    dependencies = [
        ('doctor', '0002_doctorservice'),
        ('core', '0029_fix_currency_defaults_to_xof'),
    ]

    operations = [
        migrations.RunPython(
            migrate_doctor_services_to_participant_services,
            reverse_migration
        ),
    ]
