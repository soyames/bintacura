from django.db import transaction
from .models import *

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
from django.db import transaction
from .models import *

class WearableDataService:  # Service class for WearableData operations
    @staticmethod
    def create_wearabledata(data):  # Create wearabledata
        return WearableData.objects.create(**data)

    @staticmethod
    def get_wearabledata(pk):  # Get wearabledata
        try:
            return WearableData.objects.get(pk=pk)
        except WearableData.DoesNotExist:
            return None

    @staticmethod
    def update_wearabledata(pk, data):  # Update wearabledata
        obj = WearableDataService.get_wearabledata(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_wearabledata(pk):  # Delete wearabledata
        obj = WearableDataService.get_wearabledata(pk)
        if obj:
            obj.delete()
            return True
        return False
