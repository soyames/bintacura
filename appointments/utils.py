from datetime import time
from appointments.models import Availability


def create_default_availability_slots(participant):
    """
    Creates default 24/7 availability slots with 30-minute intervals for doctors and hospitals.
    Only creates slots for days that don't already have slots defined.
    """
    if participant.role not in ['doctor', 'hospital']:
        return
    
    weekday_map = {
        0: 'monday',
        1: 'tuesday',
        2: 'wednesday',
        3: 'thursday',
        4: 'friday',
        5: 'saturday',
        6: 'sunday'
    }
    
    for weekday_num, weekday_name in weekday_map.items():
        existing_slots = Availability.objects.filter(
            participant=participant,
            weekday=weekday_name
        ).exists()
        
        if not existing_slots:
            slots_to_create = []
            hour = 0
            minute = 0
            
            while hour < 24:
                start_time = time(hour, minute)
                
                minute += 30
                if minute >= 60:
                    minute = 0
                    hour += 1
                
                if hour < 24:
                    end_time = time(hour, minute)
                else:
                    end_time = time(23, 59)
                
                slots_to_create.append(
                    Availability(
                        participant=participant,
                        weekday=weekday_name,
                        start_time=start_time,
                        end_time=end_time,
                        slot_duration=30,
                        is_active=True
                    )
                )
                
                if hour == 23 and minute == 30:
                    break
            
            Availability.objects.bulk_create(slots_to_create)
            print(f"Created {len(slots_to_create)} default slots for {participant.full_name} on {weekday_name}")

