import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from core.models import Participant, Wallet, Transaction as CoreTransaction
from .fee_service import FeeCalculationService
from .models import PaymentReceipt

logger = logging.getLogger(__name__)


class ServicePaymentService:
    """Handle service payments (appointments, prescriptions, etc.) with proper fee calculation"""
    
    @staticmethod
    @transaction.atomic
    def process_wallet_payment(
        patient: Participant,
        provider: Participant,
        amount: Decimal,
        currency: str,
        service_type: str,
        service_id: str,
        description: str
    ) -> dict:
        """
        Process a service payment using wallet balance
        Applies 1% BINTACURA platform fee + tax
        
        Args:
            patient: Patient making the payment
            provider: Service provider receiving payment
            amount: Service amount
            currency: Currency code
            service_type: Type of service (appointment, prescription, etc.)
            service_id: ID of the service
            description: Payment description
            
        Returns:
            dict with transaction details
        """
        # Get patient wallet
        patient_wallet = Wallet.objects.select_for_update().get(participant=patient)
        
        # Check sufficient balance
        if patient_wallet.balance < amount:
            raise ValueError(f"Insufficient wallet balance. Available: {patient_wallet.balance}, Required: {amount}")
        
        # Calculate fees (1% platform fee + tax)
        fee_calculation = FeeCalculationService.calculate_service_payment_fees(
            amount,
            payment_method='wallet'
        )
        
        # Get or create provider wallet
        provider_wallet, _ = Wallet.objects.select_for_update().get_or_create(
            participant=provider,
            defaults={'currency': currency, 'balance': Decimal('0.00')}
        )
        
        # Debit patient wallet (full service amount)
        patient_balance_before = patient_wallet.balance
        patient_balance_after = patient_balance_before - amount
        
        # Create patient transaction (debit)
        patient_txn = CoreTransaction.objects.create(
            transaction_ref=f"PAY-{timezone.now().strftime('%Y%m%d%H%M%S')}-{service_id[:8]}",
            wallet=patient_wallet,
            transaction_type='payment',
            amount=amount,
            currency=currency,
            status='completed',
            payment_method='wallet',
            description=description,
            recipient=provider,
            balance_before=patient_balance_before,
            balance_after=patient_balance_after,
            completed_at=timezone.now(),
            metadata={
                'service_type': service_type,
                'service_id': service_id,
                'payment_method': 'wallet',
                'fee_calculation': {
                    'gross_amount': str(fee_calculation['gross_amount']),
                    'platform_fee': str(fee_calculation['platform_fee']),
                    'tax': str(fee_calculation['tax']),
                    'total_fee': str(fee_calculation['total_fee']),
                    'net_to_provider': str(fee_calculation['net_amount'])
                }
            }
        )
        
        # Update patient wallet
        patient_wallet.balance = patient_balance_after
        patient_wallet.last_transaction_date = timezone.now()
        patient_wallet.save()
        
        # Credit provider wallet (amount minus fees)
        net_amount = fee_calculation['net_amount']
        provider_balance_before = provider_wallet.balance
        provider_balance_after = provider_balance_before + net_amount
        
        # Create provider transaction (credit)
        provider_txn = CoreTransaction.objects.create(
            transaction_ref=f"RCV-{timezone.now().strftime('%Y%m%d%H%M%S')}-{service_id[:8]}",
            wallet=provider_wallet,
            transaction_type='payment',
            amount=net_amount,
            currency=currency,
            status='completed',
            payment_method='wallet',
            description=f"Payment received via BINTACURA Wallet - {description}",
            sender=patient,
            balance_before=provider_balance_before,
            balance_after=provider_balance_after,
            completed_at=timezone.now(),
            metadata={
                'service_type': service_type,
                'service_id': service_id,
                'payment_method': 'wallet',
                'original_amount': str(amount),
                'platform_fee_deducted': str(fee_calculation['platform_fee']),
                'tax_deducted': str(fee_calculation['tax']),
                'total_fee_deducted': str(fee_calculation['total_fee']),
                'net_received': str(net_amount)
            }
        )
        
        # Update provider wallet
        provider_wallet.balance = provider_balance_after
        provider_wallet.last_transaction_date = timezone.now()
        provider_wallet.save()
        
        logger.info(
            f"Wallet payment processed: {amount} {currency} from {patient.email} to {provider.email}. "
            f"Fee: {fee_calculation['total_fee']}, Net to provider: {net_amount}"
        )
        
        return {
            'success': True,
            'patient_transaction': patient_txn,
            'provider_transaction': provider_txn,
            'fee_calculation': fee_calculation,
            'patient_new_balance': patient_balance_after,
            'provider_new_balance': provider_balance_after
        }
    
    @staticmethod
    @transaction.atomic
    def record_onsite_payment(
        patient: Participant,
        provider: Participant,
        amount: Decimal,
        currency: str,
        service_type: str,
        service_id: str,
        description: str
    ) -> dict:
        """
        Record an on-site (cash) payment
        Still applies 1% platform fee + tax (to be deducted during payout)
        
        Args:
            patient: Patient who made payment
            provider: Service provider who received payment
            amount: Service amount
            currency: Currency code
            service_type: Type of service
            service_id: ID of the service
            description: Payment description
            
        Returns:
            dict with transaction details
        """
        # Calculate fees (same 1% + tax applies)
        fee_calculation = FeeCalculationService.calculate_service_payment_fees(
            amount,
            payment_method='onsite'
        )
        
        # Get or create provider wallet (to track on-site earnings)
        provider_wallet, _ = Wallet.objects.get_or_create(
            participant=provider,
            defaults={'currency': currency, 'balance': Decimal('0.00')}
        )
        
        # Create patient transaction record (for tracking purposes)
        patient_txn = CoreTransaction.objects.create(
            transaction_ref=f"ONSITE-{timezone.now().strftime('%Y%m%d%H%M%S')}-{service_id[:8]}",
            wallet=None,  # No wallet debit for on-site
            transaction_type='payment',
            amount=amount,
            currency=currency,
            status='completed',
            payment_method='cash',
            description=f"{description} (Paid On-site)",
            recipient=provider,
            sender=patient,
            balance_before=Decimal('0'),
            balance_after=Decimal('0'),
            completed_at=timezone.now(),
            metadata={
                'service_type': service_type,
                'service_id': service_id,
                'payment_method': 'onsite',
                'payment_location': 'on-site',
                'fee_calculation': {
                    'gross_amount': str(fee_calculation['gross_amount']),
                    'platform_fee': str(fee_calculation['platform_fee']),
                    'tax': str(fee_calculation['tax']),
                    'total_fee': str(fee_calculation['total_fee']),
                    'net_to_provider': str(fee_calculation['net_amount'])
                },
                'note': 'Fee will be deducted during provider payout'
            }
        )
        
        # Create provider transaction record (tracks on-site earnings)
        # Note: Balance is NOT updated for on-site payments
        provider_txn = CoreTransaction.objects.create(
            transaction_ref=f"ONSITE-RCV-{timezone.now().strftime('%Y%m%d%H%M%S')}-{service_id[:8]}",
            wallet=provider_wallet,
            transaction_type='payment',
            amount=amount,  # Record full amount received
            currency=currency,
            status='completed',
            payment_method='cash',
            description=f"Cash payment received on-site - {description}",
            sender=patient,
            balance_before=provider_wallet.balance,
            balance_after=provider_wallet.balance,  # Balance unchanged (cash payment)
            completed_at=timezone.now(),
            metadata={
                'service_type': service_type,
                'service_id': service_id,
                'payment_method': 'onsite',
                'payment_location': 'on-site',
                'original_amount': str(amount),
                'platform_fee_to_deduct': str(fee_calculation['platform_fee']),
                'tax_to_deduct': str(fee_calculation['tax']),
                'total_fee_to_deduct': str(fee_calculation['total_fee']),
                'net_after_fees': str(fee_calculation['net_amount']),
                'note': 'Fees will be deducted when provider requests payout'
            }
        )
        
        logger.info(
            f"On-site payment recorded: {amount} {currency} from {patient.email} to {provider.email}. "
            f"Fee to be deducted at payout: {fee_calculation['total_fee']}"
        )
        
        return {
            'success': True,
            'patient_transaction': patient_txn,
            'provider_transaction': provider_txn,
            'fee_calculation': fee_calculation,
            'note': 'On-site payment recorded. Fees will be deducted during payout.'
        }
    
    @staticmethod
    def generate_payment_receipt(transaction: CoreTransaction, service_provider_role=None) -> PaymentReceipt:
        """Generate a payment receipt for a transaction"""
        from .models import PaymentReceipt
        from .invoice_number_service import InvoiceNumberService
        from .qr_service import QRCodeService
        
        receipt_number = InvoiceNumberService.generate_receipt_number()
        
        invoice_number, invoice_sequence = InvoiceNumberService.generate_invoice_number(
            service_provider_role=service_provider_role
        )
        
        issued_to = transaction.wallet.participant if transaction.wallet else transaction.sender
        issued_by = transaction.recipient or transaction.sender
        
        payment_status = 'PAID' if transaction.status == 'completed' and transaction.payment_method != 'cash' else 'PENDING'
        if transaction.payment_method == 'cash' or transaction.payment_method == 'onsite_cash':
            payment_status = 'PENDING'
        
        receipt = PaymentReceipt.objects.create(
            transaction=transaction,
            receipt_number=receipt_number,
            invoice_number=invoice_number,
            invoice_sequence=invoice_sequence,
            issued_to=issued_to,
            issued_by=issued_by,
            amount=transaction.amount,
            subtotal=transaction.amount,
            total_amount=transaction.amount,
            currency=transaction.currency,
            payment_method=transaction.payment_method,
            payment_status=payment_status,
            transaction_reference=transaction.transaction_ref,
            billing_date=transaction.created_at,
            payment_date=transaction.completed_at if payment_status == 'PAID' else None,
        )
        
        QRCodeService.generate_invoice_qr_code(receipt)
        
        return receipt

