import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bintacura_backend.settings')
django.setup()

from core.models import Participant
from appointments.models import Availability
from datetime import time

def generate_slots():
    WEEKDAY_NAMES = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    doctors = Participant.objects.filter(role='doctor', is_active=True)
    hospitals = Participant.objects.filter(role='hospital', is_active=True)
    
    print(f'Found {doctors.count()} doctors and {hospitals.count()} hospitals')
    
    for participant in list(doctors) + list(hospitals):
        existing_days = set(Availability.objects.filter(participant=participant).values_list('weekday', flat=True).distinct())
        print(f'{participant.email}: Has slots for days {existing_days}')
        
        for weekday_name in WEEKDAY_NAMES:
            if weekday_name not in existing_days:
                slots_created = 0
                for hour in range(24):
                    for minute in [0, 30]:
                        if hour == 23 and minute == 30:
                            end_hour, end_minute = 23, 59
                        elif minute == 30:
                            end_hour, end_minute = hour + 1, 0
                        else:
                            end_hour, end_minute = hour, 30
                        
                        Availability.objects.create(
                            participant=participant,
                            weekday=weekday_name,
                            start_time=time(hour, minute),
                            end_time=time(end_hour, end_minute),
                            is_active=True
                        )
                        slots_created += 1
                
                print(f'  Created {slots_created} slots for {weekday_name}')
    
    print('✅ All availability slots generated!')

if __name__ == '__main__':
    generate_slots()

