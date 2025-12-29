from django.db import transaction
from .models import *

from django.db import transaction
from .models import *

class PrescriptionService:  # Service class for Prescription operations
    @staticmethod
    def create_prescription(data):  # Create prescription
        return Prescription.objects.create(**data)

    @staticmethod
    def get_prescription(pk):  # Get prescription
        try:
            return Prescription.objects.get(pk=pk)
        except Prescription.DoesNotExist:
            return None

    @staticmethod
    def update_prescription(pk, data):  # Update prescription
        obj = PrescriptionService.get_prescription(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_prescription(pk):  # Delete prescription
        obj = PrescriptionService.get_prescription(pk)
        if obj:
            obj.delete()
            return True
        return False
from django.db import transaction
from .models import *

class PrescriptionItemService:  # Service class for PrescriptionItem operations
    @staticmethod
    def create_prescriptionitem(data):  # Create prescriptionitem
        return PrescriptionItem.objects.create(**data)

    @staticmethod
    def get_prescriptionitem(pk):  # Get prescriptionitem
        try:
            return PrescriptionItem.objects.get(pk=pk)
        except PrescriptionItem.DoesNotExist:
            return None

    @staticmethod
    def update_prescriptionitem(pk, data):  # Update prescriptionitem
        obj = PrescriptionItemService.get_prescriptionitem(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_prescriptionitem(pk):  # Delete prescriptionitem
        obj = PrescriptionItemService.get_prescriptionitem(pk)
        if obj:
            obj.delete()
            return True
        return False
from django.db import transaction
from .models import *

class MedicationService:  # Service class for Medication operations
    @staticmethod
    def create_medication(data):  # Create medication
        return Medication.objects.create(**data)

    @staticmethod
    def get_medication(pk):  # Get medication
        try:
            return Medication.objects.get(pk=pk)
        except Medication.DoesNotExist:
            return None

    @staticmethod
    def update_medication(pk, data):  # Update medication
        obj = MedicationService.get_medication(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_medication(pk):  # Delete medication
        obj = MedicationService.get_medication(pk)
        if obj:
            obj.delete()
            return True
        return False
