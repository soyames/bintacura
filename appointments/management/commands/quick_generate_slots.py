from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Participant
from appointments.models import Availability
from datetime import time


class Command(BaseCommand):
    help = 'Quickly generate default availability slots for doctors and hospitals'

    def handle(self, *args, **kwargs):
        participants = Participant.objects.filter(
            role__in=['doctor', 'hospital'],
            is_active=True
        )

        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        count = 0

        with transaction.atomic():
            for participant in participants:
                existing_count = Availability.objects.filter(participant=participant).count()
                
                if existing_count >= 7:
                    self.stdout.write(f"Skipping {participant.email} - already has availability")
                    continue

                existing_days = set(
                    Availability.objects.filter(participant=participant).values_list('weekday', flat=True)
                )

                for weekday in weekdays:
                    if weekday not in existing_days:
                        Availability.objects.create(
                            participant=participant,
                            weekday=weekday,
                            start_time=time(8, 0),
                            end_time=time(18, 0),
                            slot_duration=30,
                            is_active=True
                        )
                        count += 1

                self.stdout.write(f"✓ Processed {participant.email}")

        self.stdout.write(self.style.SUCCESS(f'Created {count} availability slots'))
