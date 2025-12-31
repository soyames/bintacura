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
        participants_skipped = 0

        WEEKDAY_NAMES = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        # Default hours: 8 AM to 8 PM (12 hours)
        START_HOUR = 8
        END_HOUR = 20

        for participant in participants_to_process:
            # Check if participant already has ANY availability slots
            existing_count = Availability.objects.filter(participant=participant).count()
            
            if existing_count > 0:
                self.stdout.write(f'  ⏭️  Skipping {participant.email} (already has {existing_count} slots)')
                participants_skipped += 1
                continue

            # Create slots for all 7 days
            for weekday_index, weekday_name in enumerate(WEEKDAY_NAMES):
                for hour in range(START_HOUR, END_HOUR):
                    for minute in [0, 30]:
                        end_minute = 30 if minute == 0 else 0
                        end_hour = hour if minute == 0 else hour + 1
                        
                        try:
                            Availability.objects.create(
                                participant=participant,
                                weekday=weekday_name,
                                start_time=time(hour, minute),
                                end_time=time(end_hour, end_minute),
                                slot_duration=30,
                                is_active=True
                            )
                            slots_created += 1
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'Error creating slot: {str(e)}'))

            self.stdout.write(f'  ✅ Created slots for {participant.email}')

        self.stdout.write(self.style.SUCCESS(f'\n✅ Total slots created: {slots_created}'))
        self.stdout.write(self.style.WARNING(f'⏭️  Participants skipped (already have slots): {participants_skipped}'))
