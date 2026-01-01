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
    def initiate_online_payment(
        patient: Participant,
        provider: Participant,
        amount: Decimal,
        currency: str,
        service_type: str,
        service_id: str,
        description: str
    ) -> dict:
        """
        Initiate an online payment via FedaPay gateway
        Creates a pending transaction and returns FedaPay payment URL
        
        Args:
            patient: Patient making the payment
            provider: Service provider receiving payment
            amount: Service amount
            currency: Currency code
            service_type: Type of service (appointment, prescription, etc.)
            service_id: ID of the service
            description: Payment description
            
        Returns:
            dict with payment URL and transaction details
        """
        from .fedapay_webhook_handler import FedaPayWalletService
        from django.conf import settings
        
        # Calculate fees (1% platform fee + tax)
        fee_calculation = FeeCalculationService.calculate_service_payment_fees(
            amount,
            payment_method='online'
        )
        
        # Create pending transaction
        transaction_ref = f"ONLINE-{timezone.now().strftime('%Y%m%d%H%M%S')}-{service_id[:8]}"
        
        patient_txn = CoreTransaction.objects.create(
            transaction_ref=transaction_ref,
            wallet=None,  # No wallet involved for online payment
            transaction_type='payment',
            amount=amount,
            currency=currency,
            status='pending',
            payment_method='fedapay',
            description=description,
            recipient=provider,
            sender=patient,
            balance_before=Decimal('0'),
            balance_after=Decimal('0'),
            metadata={
                'service_type': service_type,
                'service_id': service_id,
                'payment_method': 'online',
                'payment_gateway': 'fedapay',
                'fee_calculation': {
                    'gross_amount': str(fee_calculation['gross_amount']),
                    'platform_fee': str(fee_calculation['platform_fee']),
                    'tax': str(fee_calculation['tax']),
                    'total_fee': str(fee_calculation['total_fee']),
                    'net_to_provider': str(fee_calculation['net_amount'])
                }
            }
        )
        
        # Initiate FedaPay transaction
        from .fedapay_service import FedaPayService
        
        # Get webhook URL based on environment
        fedapay_env = getattr(settings, 'FEDAPAY_ENVIRONMENT', 'sandbox')
        
        if fedapay_env == 'sandbox':
            callback_url = getattr(settings, 'FEDAPAY_WEBHOOK_SANDBOX', 'http://127.0.0.1:8080/api/v1/payments/fedapay/webhook/')
        else:
            callback_url = getattr(settings, 'FEDAPAY_WEBHOOK_LIVE', 'https://bintacura.org/api/v1/payments/fedapay/webhook/')
        
        logger.info(f"🔔 Using FedaPay webhook URL ({fedapay_env}): {callback_url}")
        
        fedapay_service = FedaPayService()
        
        # Create or get customer first
        customer_result = fedapay_service.create_or_get_customer(participant=patient)
        
        # Create transaction
        fedapay_result = fedapay_service.create_transaction(
            amount=amount,
            currency=currency,
            description=description,
            customer_id=customer_result['id'],
            callback_url=callback_url,
            custom_metadata={
                'participant_id': str(patient.uid),
                'transaction_type': 'service_payment',
                'service_transaction_id': str(patient_txn.id)
            },
            merchant_reference=f"SVC-{patient_txn.transaction_ref}"
        )
        
        # Generate payment token
        transaction_id = fedapay_result['id']
        token_result = fedapay_service.generate_payment_token(transaction_id)
        
        # Update transaction with FedaPay reference
        patient_txn.metadata['fedapay_transaction_id'] = transaction_id
        patient_txn.metadata['fedapay_reference'] = fedapay_result.get('reference')
        patient_txn.metadata['payment_url'] = token_result.get('url')
        patient_txn.metadata['payment_token'] = token_result.get('token')
        patient_txn.save()
        
        logger.info(
            f"Online payment initiated: {amount} {currency} from {patient.email} to {provider.email}. "
            f"FedaPay ID: {transaction_id}"
        )
        
        return {
            'success': True,
            'patient_transaction': patient_txn,
            'payment_url': token_result.get('url'),
            'payment_token': token_result.get('token'),
            'fedapay_transaction_id': transaction_id,
            'fee_calculation': fee_calculation,
            'transaction_ref': transaction_ref
        }
    
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
        DEPRECATED: Wallet payments are not used in BINTACURA.
        All online payments go through FedaPay.
        Use initiate_online_payment() instead.
        
        This method redirects to online payment initiation.
        """
        logger.warning(
            f"process_wallet_payment called but wallet payments not supported. "
            f"Redirecting to online payment via FedaPay for {patient.email}"
        )
        return ServicePaymentService.initiate_online_payment(
            patient=patient,
            provider=provider,
            amount=amount,
            currency=currency,
            service_type=service_type,
            service_id=service_id,
            description=description
        )
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
        
        # Determine issued_to - the patient/payer
        issued_to = None
        if transaction.wallet and transaction.wallet.participant:
            issued_to = transaction.wallet.participant
        elif transaction.sender:
            issued_to = transaction.sender
            
        # Determine issued_by - the service provider
        issued_by = None
        if transaction.recipient:
            issued_by = transaction.recipient
        
        # Get issued_to name and address
        issued_to_name = issued_to.full_name if issued_to else ''
        issued_to_address = issued_to.address if issued_to else ''
        issued_to_city = issued_to.city if issued_to else ''
        issued_to_country = issued_to.country if issued_to else ''
        
        payment_status = 'PAID' if transaction.status == 'completed' and transaction.payment_method not in ['cash', 'onsite_cash'] else 'PENDING'
        if transaction.payment_method in ['cash', 'onsite_cash', 'onsite']:
            payment_status = 'PENDING'
        
        receipt = PaymentReceipt.objects.create(
            transaction=transaction,
            receipt_number=receipt_number,
            invoice_number=invoice_number,
            invoice_sequence=invoice_sequence,
            issued_to=issued_to,
            issued_by=issued_by,
            issued_to_name=issued_to_name,
            issued_to_address=issued_to_address,
            issued_to_city=issued_to_city,
            issued_to_country=issued_to_country,
            amount=transaction.amount,
            subtotal=transaction.amount,
            total_amount=transaction.amount,
            currency=transaction.currency,
            payment_method=transaction.payment_method,
            payment_status=payment_status,
            transaction_reference=transaction.transaction_ref,
            payment_gateway='',
            gateway_transaction_id='',
            billing_date=transaction.created_at,
            payment_date=transaction.completed_at if payment_status == 'PAID' else None,
        )
        
        QRCodeService.generate_invoice_qr_code(receipt)
        
        return receipt

