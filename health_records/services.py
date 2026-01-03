from django.db import transaction
from .models import *

class HealthRecordService:  # Service class for HealthRecord operations
    @staticmethod
    def create_healthrecord(data):  # Create healthrecord
        return HealthRecord.objects.create(**data)

    @staticmethod
    def get_healthrecord(pk):  # Get healthrecord
        try:
            return HealthRecord.objects.get(pk=pk)
        except HealthRecord.DoesNotExist:
            return None

    @staticmethod
    def update_healthrecord(pk, data):  # Update healthrecord
        obj = HealthRecordService.get_healthrecord(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_healthrecord(pk):  # Delete healthrecord
        obj = HealthRecordService.get_healthrecord(pk)
        if obj:
            obj.delete()
            return True
        return False

# NOTE: WearableDataService has been moved to wearable_devices.services
# Import from there if needed:
# from wearable_devices.services import WearableDataService
