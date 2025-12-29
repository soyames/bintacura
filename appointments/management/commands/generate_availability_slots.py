from django.core.management.base import BaseCommand
from core.models import Participant
from appointments.models import Availability
from datetime import time


class Command(BaseCommand):
    help = 'Generate default 24/7 availability slots for doctors and hospitals'

    def handle(self, *args, **options):
        doctors = Participant.objects.filter(role='doctor')
        hospitals = Participant.objects.filter(role='hospital')
        participants_to_process = list(doctors) + list(hospitals)

        self.stdout.write(f'Processing {len(participants_to_process)} participants...')

        slots_created = 0
        slots_skipped = 0

        for participant in participants_to_process:
            for weekday in range(7):
                existing = Availability.objects.filter(
                    participant=participant,
                    weekday=weekday
                ).exists()
                
                if existing:
                    slots_skipped += 1
                    continue

                for hour in range(24):
                    for minute in [0, 30]:
                        end_minute = 30 if minute == 0 else 0
                        end_hour = hour if minute == 0 else (hour + 1) % 24
                        
                        weekday_name = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][weekday]
                        Availability.objects.create(
                            participant=participant,
                            weekday=weekday_name,
                            start_time=time(hour, minute),
                            end_time=time(end_hour, end_minute),
                            is_active=True
                        )
                        slots_created += 1

        self.stdout.write(self.style.SUCCESS(f'\n✅ Slots created: {slots_created}'))
        self.stdout.write(self.style.WARNING(f'⏭️  Slots skipped (already exist): {slots_skipped}'))
