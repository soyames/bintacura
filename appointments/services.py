from django.db import transaction
from .models import *

from django.db import transaction
from .models import *

class AppointmentService:  # Service class for Appointment operations
    @staticmethod
    def create_appointment(data):  # Create appointment
        return Appointment.objects.create(**data)

    @staticmethod
    def get_appointment(pk):  # Get appointment
        try:
            return Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            return None

    @staticmethod
    def update_appointment(pk, data):  # Update appointment
        obj = AppointmentService.get_appointment(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_appointment(pk):  # Delete appointment
        obj = AppointmentService.get_appointment(pk)
        if obj:
            obj.delete()
            return True
        return False
from django.db import transaction
from .models import *

class AvailabilityService:  # Service class for Availability operations
    @staticmethod
    def create_availability(data):  # Create availability
        return Availability.objects.create(**data)

    @staticmethod
    def get_availability(pk):  # Get availability
        try:
            return Availability.objects.get(pk=pk)
        except Availability.DoesNotExist:
            return None

    @staticmethod
    def update_availability(pk, data):  # Update availability
        obj = AvailabilityService.get_availability(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_availability(pk):  # Delete availability
        obj = AvailabilityService.get_availability(pk)
        if obj:
            obj.delete()
            return True
        return False
from django.db import transaction
from .models import *

class AppointmentQueueService:  # Service class for AppointmentQueue operations
    @staticmethod
    def create_appointmentqueue(data):  # Create appointmentqueue
        return AppointmentQueue.objects.create(**data)

    @staticmethod
    def get_appointmentqueue(pk):  # Get appointmentqueue
        try:
            return AppointmentQueue.objects.get(pk=pk)
        except AppointmentQueue.DoesNotExist:
            return None

    @staticmethod
    def update_appointmentqueue(pk, data):  # Update appointmentqueue
        obj = AppointmentQueueService.get_appointmentqueue(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_appointmentqueue(pk):  # Delete appointmentqueue
        obj = AppointmentQueueService.get_appointmentqueue(pk)
        if obj:
            obj.delete()
            return True
        return False
