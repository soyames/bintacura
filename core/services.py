from django.db import transaction
from decimal import Decimal
from .models import *


class ParticipantService:
    @staticmethod
    def create_participant(data):  # Creates a new participant from provided data dictionary
        return Participant.objects.create(**data)

    @staticmethod
    def get_participant(pk):  # Retrieves participant by primary key or returns None
        try:
            return Participant.objects.get(pk=pk)
        except Participant.DoesNotExist:
            return None

    @staticmethod
    def update_participant(pk, data):  # Updates participant fields with provided data
        obj = ParticipantService.get_participant(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_participant(pk):  # Deletes participant by primary key
        obj = ParticipantService.get_participant(pk)
        if obj:
            obj.delete()
            return True
        return False


from django.db import transaction
from .models import *


class ParticipantProfileService:
    @staticmethod
    def create_participant_profile(data):  # Creates a new participant profile from provided data
        return ParticipantProfile.objects.create(**data)

    @staticmethod
    def get_participant_profile(pk):  # Retrieves participant profile by primary key or returns None
        try:
            return ParticipantProfile.objects.get(pk=pk)
        except ParticipantProfile.DoesNotExist:
            return None

    @staticmethod
    def update_participant_profile(pk, data):  # Updates participant profile fields with provided data
        obj = ParticipantProfileService.get_participant_profile(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_participant_profile(pk):  # Deletes participant profile by primary key
        obj = ParticipantProfileService.get_participant_profile(pk)
        if obj:
            obj.delete()
            return True
        return False


from django.db import transaction
from .models import *


class PatientDataService:
    @staticmethod
    def create_patientdata(data):
        return PatientData.objects.create(**data)

    @staticmethod
    def get_patientdata(pk):
        try:
            return PatientData.objects.get(pk=pk)
        except PatientData.DoesNotExist:
            return None

    @staticmethod
    def update_patientdata(pk, data):
        obj = PatientDataService.get_patientdata(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_patientdata(pk):
        obj = PatientDataService.get_patientdata(pk)
        if obj:
            obj.delete()
            return True
        return False


from django.db import transaction
from .models import *


class DoctorDataService:
    @staticmethod
    def create_doctordata(data):
        return DoctorData.objects.create(**data)

    @staticmethod
    def get_doctordata(pk):
        try:
            return DoctorData.objects.get(pk=pk)
        except DoctorData.DoesNotExist:
            return None

    @staticmethod
    def update_doctordata(pk, data):
        obj = DoctorDataService.get_doctordata(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_doctordata(pk):
        obj = DoctorDataService.get_doctordata(pk)
        if obj:
            obj.delete()
            return True
        return False


from django.db import transaction
from .models import *


class ProviderDataService:
    @staticmethod
    def create_providerdata(data):
        return ProviderData.objects.create(**data)

    @staticmethod
    def get_providerdata(pk):
        try:
            return ProviderData.objects.get(pk=pk)
        except ProviderData.DoesNotExist:
            return None

    @staticmethod
    def update_providerdata(pk, data):
        obj = ProviderDataService.get_providerdata(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_providerdata(pk):
        obj = ProviderDataService.get_providerdata(pk)
        if obj:
            obj.delete()
            return True
        return False


class WalletService:
    BINTACURA_FEE_PERCENTAGE = Decimal("0.01")
    WITHDRAWAL_FEE_PERCENTAGE = Decimal("0.01")
    TRANSFER_FEE = Decimal("0.50")

    @staticmethod
    @transaction.atomic
    def create_wallet(participant, currency="EUR"):  # Creates or retrieves wallet for participant with specified currency
        wallet, created = Wallet.objects.get_or_create(
            participant=participant, defaults={"currency": currency, "balance": 0.00}
        )
        return wallet

    @staticmethod
    def get_wallet(participant):  # Retrieves participant wallet or creates one if not exists
        try:
            return Wallet.objects.get(participant=participant)
        except Wallet.DoesNotExist:
            return WalletService.create_wallet(participant)

    @staticmethod
    @transaction.atomic
    def deposit(  # Deposits money into participant wallet and creates transaction record
        participant,
        amount,
        payment_method="card",
        description="Deposit to wallet",
        metadata=None,
    ):
        amount = Decimal(str(amount))
        wallet = WalletService.get_wallet(participant)

        if wallet.status != "active":
            raise ValueError(f"Wallet is {wallet.status}. Cannot perform deposit.")

        if amount <= 0:
            raise ValueError("Deposit amount must be greater than zero.")

        balance_before = wallet.balance
        balance_after = wallet.balance + amount

        txn = Transaction.objects.create(
            wallet=wallet,
            transaction_type="deposit",
            amount=amount,
            currency=wallet.currency,
            payment_method=payment_method,
            status="completed",
            description=description,
            balance_before=balance_before,
            balance_after=balance_after,
            metadata=metadata or {},
        )

        wallet.balance = balance_after
        wallet.save()

        ParticipantActivityLog.objects.create(
            participant=participant,
            activity_type="wallet_deposit",
            description=f"Deposited {wallet.currency} {amount} via {payment_method}",
            metadata={
                "transaction_ref": str(txn.transaction_ref),
                "amount": str(amount),
            },
        )

        return txn

    @staticmethod
    @transaction.atomic
    def make_payment(  # Processes payment from patient to recipient with platform fee deduction
        patient,
        recipient,
        amount,
        description="Payment",
        payment_method="wallet",
        metadata=None,
    ):
        amount = Decimal(str(amount))
        patient_wallet = WalletService.get_wallet(patient)
        recipient_wallet = WalletService.get_wallet(recipient)

        if patient_wallet.status != "active":
            raise ValueError(
                f"Le portefeuille du patient est {patient_wallet.status}. Impossible d'effectuer le paiement."
            )

        if recipient_wallet.status != "active":
            raise ValueError(
                f"Le portefeuille du destinataire est {recipient_wallet.status}. Impossible de recevoir le paiement."
            )

        if amount <= 0:
            raise ValueError("Le montant du paiement doit être supérieur à zéro.")

        is_cash_payment = payment_method in ['cash', 'onsite_cash', 'onsite']
        transaction_status = 'pending' if is_cash_payment else 'completed'
        
        if not is_cash_payment and patient_wallet.balance < amount:
            raise ValueError(
                f"Solde insuffisant. Disponible: {patient_wallet.balance} {patient_wallet.currency}"
            )

        platform_fee = amount * WalletService.BINTACURA_FEE_PERCENTAGE
        recipient_net_amount = amount - platform_fee

        # Calculate final balances
        patient_balance_before = patient_wallet.balance
        patient_balance_after = patient_wallet.balance - amount if not is_cash_payment else patient_wallet.balance
        recipient_balance_before = recipient_wallet.balance
        recipient_balance_after = recipient_wallet.balance + recipient_net_amount if not is_cash_payment else recipient_wallet.balance

        patient_txn = Transaction.objects.create(
            wallet=patient_wallet,
            transaction_type="payment",
            amount=amount,
            currency=patient_wallet.currency,
            payment_method=payment_method,
            status=transaction_status,
            description=description,
            recipient=recipient,
            balance_before=patient_balance_before,
            balance_after=patient_balance_after,
            metadata=metadata or {},
        )

        if not is_cash_payment:
            patient_wallet.balance = patient_balance_after
            patient_wallet.save()

        recipient_txn = Transaction.objects.create(
            wallet=recipient_wallet,
            transaction_type="payment",
            amount=recipient_net_amount,
            currency=recipient_wallet.currency,
            payment_method="wallet",
            status=transaction_status,
            description=f"Payment received from {patient.full_name or patient.email}",
            sender=patient,
            balance_before=recipient_balance_before,
            balance_after=recipient_balance_after,
            metadata={
                "gross_amount": str(amount),
                "platform_fee": str(platform_fee),
                "patient_transaction_ref": str(patient_txn.transaction_ref),
            },
        )

        if not is_cash_payment:
            recipient_wallet.balance = recipient_balance_after
            recipient_wallet.save()

        fee_txn = Transaction.objects.create(
            wallet=recipient_wallet,
            transaction_type="fee",
            amount=platform_fee,
            currency=recipient_wallet.currency,
            payment_method="wallet",
            status=transaction_status,
            description="BINTACURA platform fee",
            balance_before=recipient_balance_after,
            balance_after=recipient_balance_after,
            metadata={
                "original_transaction": str(patient_txn.transaction_ref),
                "fee_percentage": str(WalletService.BINTACURA_FEE_PERCENTAGE * 100),
            },
        )

        ParticipantActivityLog.objects.create(
            participant=patient,
            activity_type="payment_sent",
            description=f"Paid {patient_wallet.currency} {amount} to {recipient.full_name or recipient.email}",
            metadata={"transaction_ref": str(patient_txn.transaction_ref)},
        )

        ParticipantActivityLog.objects.create(
            participant=recipient,
            activity_type="payment_received",
            description=f"Received {recipient_wallet.currency} {recipient_net_amount} from {patient.full_name or patient.email}",
            metadata={"transaction_ref": str(recipient_txn.transaction_ref)},
        )

        return {
            "patient_transaction": patient_txn,
            "recipient_transaction": recipient_txn,
            "fee_transaction": fee_txn,
            "platform_fee": platform_fee,
        }

    @staticmethod
    @transaction.atomic
    def refund_payment(original_transaction_ref, reason="Refund"):  # Refunds a completed payment transaction by reversing wallet balances
        try:
            original_txn = Transaction.objects.get(
                transaction_ref=original_transaction_ref, transaction_type="payment"
            )
        except Transaction.DoesNotExist:
            raise ValueError(f"Transaction {original_transaction_ref} not found")

        if original_txn.status != "completed":
            raise ValueError("Can only refund completed transactions")

        patient = (
            original_txn.recipient
            if original_txn.sender
            else original_txn.wallet.participant
        )
        recipient = (
            original_txn.sender if original_txn.sender else original_txn.recipient
        )

        patient_wallet = WalletService.get_wallet(patient)
        recipient_wallet = WalletService.get_wallet(recipient)

        amount = original_txn.amount

        # Calculate final balances
        recipient_balance_before = recipient_wallet.balance
        recipient_balance_after = recipient_wallet.balance - amount
        patient_balance_before = patient_wallet.balance
        patient_balance_after = patient_wallet.balance + amount

        # Debit recipient wallet
        recipient_refund_txn = Transaction.objects.create(
            wallet=recipient_wallet,
            transaction_type="refund",
            amount=amount,
            currency=recipient_wallet.currency,
            payment_method="wallet",
            status="completed",
            description=f"Refund: {reason}",
            recipient=patient,
            balance_before=recipient_balance_before,
            balance_after=recipient_balance_after,
            metadata={"original_transaction": str(original_transaction_ref)},
        )

        recipient_wallet.balance = recipient_balance_after
        recipient_wallet.save()

        patient_refund_txn = Transaction.objects.create(
            wallet=patient_wallet,
            transaction_type="refund",
            amount=amount,
            currency=patient_wallet.currency,
            payment_method="wallet",
            status="completed",
            description=f"Refund received: {reason}",
            sender=recipient,
            balance_before=patient_balance_before,
            balance_after=patient_balance_after,
            metadata={"original_transaction": str(original_transaction_ref)},
        )

        patient_wallet.balance = patient_balance_after
        patient_wallet.save()

        return {
            "patient_refund": patient_refund_txn,
            "recipient_refund": recipient_refund_txn,
        }

    @staticmethod
    @transaction.atomic
    def transfer_funds(sender, recipient_email, amount, description="Fund transfer"):  # Transfers funds between participants with transfer fee applied
        amount = Decimal(str(amount))
        try:
            recipient = Participant.objects.get(email=recipient_email)
        except Participant.DoesNotExist:
            raise ValueError(f"Recipient with email {recipient_email} not found")

        sender_wallet = WalletService.get_wallet(sender)
        recipient_wallet = WalletService.get_wallet(recipient)

        if sender_wallet.balance < (amount + WalletService.TRANSFER_FEE):
            raise ValueError(
                f"Insufficient balance. Need {amount + WalletService.TRANSFER_FEE} (including {WalletService.TRANSFER_FEE} fee)"
            )

        # Calculate final balances
        sender_balance_before = sender_wallet.balance
        sender_balance_after = sender_wallet.balance - (
            amount + WalletService.TRANSFER_FEE
        )
        recipient_balance_before = recipient_wallet.balance
        recipient_balance_after = recipient_wallet.balance + amount

        sender_txn = Transaction.objects.create(
            wallet=sender_wallet,
            transaction_type="transfer",
            amount=amount + WalletService.TRANSFER_FEE,
            currency=sender_wallet.currency,
            payment_method="wallet",
            status="completed",
            description=description,
            recipient=recipient,
            balance_before=sender_balance_before,
            balance_after=sender_balance_after,
            metadata={"transfer_fee": str(WalletService.TRANSFER_FEE)},
        )

        sender_wallet.balance = sender_balance_after
        sender_wallet.save()

        recipient_txn = Transaction.objects.create(
            wallet=recipient_wallet,
            transaction_type="transfer",
            amount=amount,
            currency=recipient_wallet.currency,
            payment_method="wallet",
            status="completed",
            description=f"Transfer from {sender.full_name or sender.email}",
            sender=sender,
            balance_before=recipient_balance_before,
            balance_after=recipient_balance_after,
            metadata={"sender_transaction": str(sender_txn.transaction_ref)},
        )

        recipient_wallet.balance = recipient_balance_after
        recipient_wallet.save()

        return {
            "sender_transaction": sender_txn,
            "recipient_transaction": recipient_txn,
        }

    @staticmethod
    @transaction.atomic
    def withdraw_to_bank(  # Withdraws funds from wallet to bank account with withdrawal fee
        participant, amount, bank_account_info, description="Withdrawal to bank"
    ):
        amount = Decimal(str(amount))
        wallet = WalletService.get_wallet(participant)

        if wallet.status != "active":
            raise ValueError(f"Wallet is {wallet.status}. Cannot withdraw.")

        withdrawal_fee = amount * WalletService.WITHDRAWAL_FEE_PERCENTAGE
        total_deduction = amount + withdrawal_fee

        if wallet.balance < total_deduction:
            raise ValueError(
                f"Insufficient balance. Need {total_deduction} (including {withdrawal_fee} fee)"
            )

        # Calculate final balances
        balance_before = wallet.balance
        balance_after = wallet.balance - total_deduction

        withdrawal_txn = Transaction.objects.create(
            wallet=wallet,
            transaction_type="withdrawal",
            amount=amount,
            currency=wallet.currency,
            payment_method="bank_transfer",
            status="completed",
            description=description,
            balance_before=balance_before,
            balance_after=balance_after,
            metadata={
                "bank_account": bank_account_info,
                "withdrawal_fee": str(withdrawal_fee),
                "net_amount": str(amount),
                "total_deduction": str(total_deduction),
            },
        )

        wallet.balance = balance_after
        wallet.save()

        fee_txn = Transaction.objects.create(
            wallet=wallet,
            transaction_type="fee",
            amount=withdrawal_fee,
            currency=wallet.currency,
            payment_method="wallet",
            status="completed",
            description="Withdrawal processing fee",
            balance_before=balance_after,
            balance_after=balance_after,
            metadata={
                "withdrawal_transaction": str(withdrawal_txn.transaction_ref),
                "fee_percentage": str(WalletService.WITHDRAWAL_FEE_PERCENTAGE * 100),
            },
        )

        ParticipantActivityLog.objects.create(
            participant=participant,
            activity_type="withdrawal",
            description=f"Withdrew {wallet.currency} {amount} to bank account",
            metadata={"transaction_ref": str(withdrawal_txn.transaction_ref)},
        )

        return {"withdrawal": withdrawal_txn, "fee": fee_txn}

    @staticmethod
    def get_transaction_history(  # Retrieves transaction history for participant with optional filters
        participant, limit=50, transaction_type=None, status=None
    ):
        wallet = WalletService.get_wallet(participant)

        transactions = Transaction.objects.filter(wallet=wallet).order_by("-created_at")

        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)

        if status:
            transactions = transactions.filter(status=status)

        return transactions[:limit]

    @staticmethod
    def get_wallet_balance(participant):  # Returns wallet balance, currency and status for participant
        wallet = WalletService.get_wallet(participant)
        return {
            "balance": wallet.balance,
            "currency": wallet.currency,
            "status": wallet.status,
        }

    @staticmethod
    @transaction.atomic
    def suspend_wallet(participant, reason=""):  # Suspends participant wallet and logs activity
        wallet = WalletService.get_wallet(participant)
        wallet.status = "suspended"
        wallet.save()

        ParticipantActivityLog.objects.create(
            participant=participant,
            activity_type="wallet_suspended",
            description=f"Wallet suspended: {reason}",
            metadata={"previous_status": "active"},
        )

        return wallet

    @staticmethod
    @transaction.atomic
    def activate_wallet(participant):  # Activates suspended wallet and logs activity
        wallet = WalletService.get_wallet(participant)
        wallet.status = "active"
        wallet.save()

        ParticipantActivityLog.objects.create(
            participant=participant,
            activity_type="wallet_activated",
            description="Wallet activated",
            metadata={"previous_status": "suspended"},
        )

        return wallet

    @staticmethod
    def generate_receipt(transaction_ref):  # Generates receipt data dictionary for transaction reference
        try:
            txn = Transaction.objects.get(transaction_ref=transaction_ref)
        except Transaction.DoesNotExist:
            raise ValueError(f"Transaction {transaction_ref} not found")

        return {
            "transaction_ref": txn.transaction_ref,
            "date": txn.created_at,
            "type": txn.get_transaction_type_display(),
            "amount": txn.amount,
            "currency": txn.currency,
            "status": txn.get_status_display(),
            "description": txn.description,
            "payment_method": txn.get_payment_method_display(),
            "balance_before": txn.balance_before,
            "balance_after": txn.balance_after,
            "wallet_owner": txn.wallet.participant.full_name
            or txn.wallet.participant.email,
            "wallet_owner_email": txn.wallet.participant.email,
            "recipient": (txn.recipient.full_name or txn.recipient.email)
            if txn.recipient
            else None,
            "sender": (txn.sender.full_name or txn.sender.email)
            if txn.sender
            else None,
            "metadata": txn.metadata,
        }

    @staticmethod
    def add_payment_method(  # Adds new payment method for participant and logs activity
        participant,
        method_type,
        provider_name,
        account_identifier,
        external_token="",
        is_default=False,
        metadata=None,
    ):
        if is_default:
            PaymentMethod.objects.filter(
                participant=participant, is_default=True
            ).update(is_default=False)

        payment_method = PaymentMethod.objects.create(
            participant=participant,
            method_type=method_type,
            provider_name=provider_name,
            account_identifier=account_identifier,
            external_token=external_token,
            is_default=is_default,
            metadata=metadata or {},
        )

        ParticipantActivityLog.objects.create(
            participant=participant,
            activity_type="payment_method_added",
            description=f"Added {method_type} payment method: {provider_name}",
            metadata={"payment_method_id": str(payment_method.id)},
        )

        return payment_method

    @staticmethod
    def get_payment_methods(participant):  # Returns all active payment methods for participant
        return PaymentMethod.objects.filter(
            participant=participant, status="active"
        ).order_by("-is_default", "-created_at")

    @staticmethod
    @transaction.atomic
    def charge_external_payment(participant, amount, payment_method_id=None):  # Charges external payment method and updates last used timestamp
        amount = Decimal(str(amount))

        if payment_method_id:
            try:
                payment_method = PaymentMethod.objects.get(
                    id=payment_method_id, participant=participant, status="active"
                )
            except PaymentMethod.DoesNotExist:
                raise ValueError("Payment method not found or inactive")
        else:
            payment_method = (
                PaymentMethod.objects.filter(
                    participant=participant, status="active", is_default=True
                )
                .order_by("-is_default")
                .first()
            )
            if not payment_method:
                raise ValueError("No default payment method found")

        payment_method.last_used_at = timezone.now()
        payment_method.save()

        return {
            "success": True,
            "payment_method": payment_method,
            "amount": amount,
            "message": f"External payment gateway integration pending for {payment_method.method_type}",
        }

    @staticmethod
    @transaction.atomic
    def top_up_wallet_via_external(  # Tops up wallet using external payment method
        participant, amount, payment_method_id=None, description="Wallet top-up"
    ):
        amount = Decimal(str(amount))

        charge_result = WalletService.charge_external_payment(
            participant, amount, payment_method_id
        )

        if charge_result["success"]:
            deposit_txn = WalletService.deposit(
                participant,
                amount,
                payment_method=charge_result["payment_method"].method_type,
                description=description,
                metadata={
                    "external_payment_method": str(charge_result["payment_method"].id),
                    "provider": charge_result["payment_method"].provider_name,
                },
            )

            return {"success": True, "transaction": deposit_txn}
        else:
            raise ValueError("External payment failed")

