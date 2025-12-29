from django.db import transaction
from .models import *


class TransactionService:  # Service class for Transaction operations
    @staticmethod
    def create_transaction(data):  # Create transaction
        return Transaction.objects.create(**data)

    @staticmethod
    def get_transaction(pk):  # Get transaction
        try:
            return Transaction.objects.get(pk=pk)
        except Transaction.DoesNotExist:
            return None

    @staticmethod
    def update_transaction(pk, data):  # Update transaction
        obj = TransactionService.get_transaction(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_transaction(pk):  # Delete transaction
        obj = TransactionService.get_transaction(pk)
        if obj:
            obj.delete()
            return True
        return False


from django.db import transaction
from .models import *


class FeeLedgerService:  # Service class for FeeLedger operations
    @staticmethod
    def create_feeledger(data):  # Create feeledger
        return FeeLedger.objects.create(**data)

    @staticmethod
    def get_feeledger(pk):  # Get feeledger
        try:
            return FeeLedger.objects.get(pk=pk)
        except FeeLedger.DoesNotExist:
            return None

    @staticmethod
    def update_feeledger(pk, data):  # Update feeledger
        obj = FeeLedgerService.get_feeledger(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_feeledger(pk):  # Delete feeledger
        obj = FeeLedgerService.get_feeledger(pk)
        if obj:
            obj.delete()
            return True
        return False
