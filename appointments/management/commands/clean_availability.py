from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Participant
from appointments.models import Availability
from datetime import time


class Command(BaseCommand):
    help = 'Clean up duplicate availability slots and ensure proper setup'

    def handle(self, *args, **kwargs):
        participants = Participant.objects.filter(
            role__in=['doctor', 'hospital'],
            is_active=True
        )

        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for participant in participants:
            self.stdout.write(f"\nProcessing {participant.email}...")
            
            # Delete all existing
            deleted_count = Availability.objects.filter(participant=participant).delete()[0]
            self.stdout.write(f"  Deleted {deleted_count} old records")
            
            # Create one record per weekday: 8 AM - 6 PM, 30-min slots
            created_count = 0
            for weekday in weekdays:
                Availability.objects.create(
                    participant=participant,
                    weekday=weekday,
                    start_time=time(8, 0),
                    end_time=time(18, 0),
                    slot_duration=30,
                    is_active=True
                )
                created_count += 1
            
            self.stdout.write(self.style.SUCCESS(f"  ✓ Created {created_count} availability records"))

        self.stdout.write(self.style.SUCCESS('\nDone! All participants now have clean availability slots.'))
