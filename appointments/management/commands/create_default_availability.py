from django.core.management.base import BaseCommand
from django.db import transaction
from appointments.models import Availability
from core.models import Participant
from datetime import time


class Command(BaseCommand):
    help = 'Create default 24/7 availability slots for hospitals and doctors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Delete existing availability and create new ones',
        )

    def handle(self, *args, **options):
        overwrite = options.get('overwrite', False)
        
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        hospitals = Participant.objects.filter(role='hospital', is_active=True)
        doctors = Participant.objects.filter(role='doctor', is_active=True)
        
        self.stdout.write(f"Found {hospitals.count()} hospitals and {doctors.count()} doctors")
        
        with transaction.atomic():
            for participant in list(hospitals) + list(doctors):
                existing_count = Availability.objects.filter(participant=participant).count()
                
                if existing_count > 0 and not overwrite:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping {participant.role} {participant.uid} - already has {existing_count} availability slots"
                        )
                    )
                    continue
                
                if overwrite and existing_count > 0:
                    deleted_count = Availability.objects.filter(participant=participant).delete()[0]
                    self.stdout.write(
                        self.style.WARNING(f"Deleted {deleted_count} existing slots for {participant.uid}")
                    )
                
                created_count = 0
                for weekday in weekdays:
                    availability = Availability.objects.create(
                        participant=participant,
                        weekday=weekday,
                        start_time=time(0, 0),
                        end_time=time(23, 30),
                        slot_duration=30,
                        is_active=True
                    )
                    created_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created {created_count} availability slots for {participant.role} {participant.uid}"
                    )
                )
        
        self.stdout.write(self.style.SUCCESS('Successfully created default availability slots'))
