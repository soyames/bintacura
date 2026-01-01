from decimal import Decimal
from django.utils import timezone
from django.db import transaction
import logging

from currency_converter.services import CurrencyConverterService
from .models import (
    ServiceTransaction,
    GatewayTransaction,
    TransactionFee,
    PaymentReceipt,
)

logger = logging.getLogger(__name__)


class PaymentOrchestrationService:
    """
    FINAL PAYMENT MODEL IMPLEMENTATION
    
    Implements BintaCura's payment orchestration as per Final Payment.md:
    1. All payments go through external gateways
    2. USD is the base/reference currency
    3. Participant local currency is used for execution
    4. 1% platform commission is applied
    5. 18% tax is applied when applicable
    6. Dual currency tracking (USD + local) for audit
    7. No wallet custody - only transaction recording
    """
    
    PLATFORM_COMMISSION_RATE = Decimal('0.01')
    TAX_RATE = Decimal('0.18')
    
    @classmethod
    def create_payment_intent(cls, patient, service_provider, service_details, amount_xof):
        """
        Create payment intent for ANY payment type through BintaCura.
        
        Args:
            patient: Participant (payer)
            service_provider: Participant (payee)
            service_details: dict with service_type, service_id, description
            amount_xof: Decimal amount in XOF (base currency)
        
        Returns:
            ServiceTransaction with dual currency tracking
        """
        try:
            local_currency = CurrencyConverterService.get_participant_currency(patient)
            amount_local, _ = CurrencyConverterService.convert_to_local_currency(
                amount_xof, patient
            )
            exchange_rate = CurrencyConverterService.get_rate('XOF', local_currency)
            
            logger.info(
                f"Payment intent: {amount_xof} XOF = {amount_local} {local_currency} "
                f"(rate: {exchange_rate})"
            )
            
            with transaction.atomic():
                service_transaction = ServiceTransaction.objects.create(
                    patient=patient,
                    service_provider=service_provider,
                    service_provider_role=service_provider.role,
                    service_type=service_details.get('service_type', 'other'),
                    service_id=service_details.get('service_id'),
                    service_description=service_details.get('description', ''),
                    
                    amount_usd=amount_xof,
                    amount_local=amount_local,
                    currency_code=local_currency,
                    exchange_rate_used=exchange_rate,
                    conversion_timestamp=timezone.now(),
                    
                    amount=amount_local,
                    currency=local_currency,
                    payment_method=service_details.get('payment_method', 'fedapay_mobile'),
                    status='pending',
                    metadata=service_details.get('metadata', {})
                )
                
                cls._calculate_and_store_fees(service_transaction, amount_xof, amount_local, local_currency, exchange_rate)
                
                logger.info(f"Payment intent created: {service_transaction.transaction_ref}")
                return service_transaction
                
        except Exception as e:
            logger.error(f"Failed to create payment intent: {e}")
            raise
    
    @classmethod
    def _calculate_and_store_fees(cls, service_transaction, amount_xof, amount_local, local_currency, exchange_rate):
        """
        Calculate commission and tax in both XOF and local currency.
        
        CRITICAL: Commission is calculated on XOF amount, then converted to local currency.
        This ensures consistency across all instances and audit trails.
        """
        commission_xof = amount_xof * cls.PLATFORM_COMMISSION_RATE
        commission_local = commission_xof * exchange_rate
        
        tax_xof = amount_xof * cls.TAX_RATE
        tax_local = tax_xof * exchange_rate
        
        if local_currency in ['XOF', 'XAF', 'NGN', 'KES']:
            commission_local = commission_local.quantize(Decimal('1'))
            tax_local = tax_local.quantize(Decimal('1'))
        else:
            commission_local = commission_local.quantize(Decimal('0.01'))
            tax_local = tax_local.quantize(Decimal('0.01'))
        
        total_fee = commission_local + tax_local
        net_to_provider = amount_local - total_fee
        
        TransactionFee.objects.create(
            service_transaction=service_transaction,
            
            gross_amount_usd=amount_xof,
            gross_amount_local=amount_local,
            currency_code=local_currency,
            exchange_rate_used=exchange_rate,
            
            gross_amount=amount_local,
            
            platform_fee_rate=cls.PLATFORM_COMMISSION_RATE,
            platform_fee_amount_usd=commission_xof,
            platform_fee_amount_local=commission_local,
            platform_fee_amount=commission_local,
            
            tax_rate=cls.TAX_RATE,
            tax_amount_usd=tax_xof,
            tax_amount_local=tax_local,
            tax_amount=tax_local,
            
            total_fee_amount=total_fee,
            net_amount_to_provider=net_to_provider,
            fee_collected=False,
        )
        
        logger.info(
            f"Fees calculated - Commission: {commission_usd} USD ({commission_local} {local_currency}), "
            f"Tax: {tax_usd} USD ({tax_local} {local_currency})"
        )
    
    @classmethod
    def initiate_gateway_payment(cls, service_transaction, payment_method, patient_phone=None):
        """
        Initiate payment through external gateway.
        
        POLICY: All payments go through external gateways with split payment instructions:
        - Provider share (amount - commission)
        - BintaCura 1% commission
        
        Gateway must support split payments or is not supported.
        """
        try:
            fee_details = service_transaction.fee_details
            
            gateway_transaction = GatewayTransaction.objects.create(
                gateway_provider=cls._determine_gateway_provider(payment_method),
                transaction_type='payment_collection',
                payment_context='patient_service',
                
                patient=service_transaction.patient,
                service_provider=service_transaction.service_provider,
                patient_phone=patient_phone,
                
                amount_usd=service_transaction.amount_usd,
                amount_local=service_transaction.amount_local,
                currency_code=service_transaction.currency_code,
                exchange_rate_used=service_transaction.exchange_rate_used,
                conversion_timestamp=service_transaction.conversion_timestamp,
                
                amount=service_transaction.amount_local,
                currency=service_transaction.currency_code,
                payment_method=payment_method,
                
                commission=fee_details.platform_fee_amount_local,
                commission_rate=cls.PLATFORM_COMMISSION_RATE,
                fees=fee_details.tax_amount_local,
                
                status='pending',
                metadata={
                    'service_transaction_id': str(service_transaction.id),
                    'service_type': service_transaction.service_type,
                    'split_instructions': {
                        'provider_share': str(fee_details.net_amount_to_provider),
                        'platform_commission': str(fee_details.platform_fee_amount_local),
                        'currency': service_transaction.currency_code,
                    }
                }
            )
            
            service_transaction.gateway_transaction = gateway_transaction
            service_transaction.status = 'processing'
            service_transaction.save()
            
            logger.info(f"Gateway payment initiated: {gateway_transaction.gateway_reference}")
            return gateway_transaction
            
        except Exception as e:
            logger.error(f"Failed to initiate gateway payment: {e}")
            service_transaction.status = 'failed'
            service_transaction.save()
            raise
    
    @classmethod
    def _determine_gateway_provider(cls, payment_method):
        """Map payment method to gateway provider"""
        if payment_method.startswith('fedapay'):
            return 'fedapay'
        elif payment_method == 'mtn_momo':
            return 'mtn_momo'
        elif payment_method == 'moov_money':
            return 'moov_money'
        elif payment_method == 'orange_money':
            return 'orange_money'
        else:
            return 'fedapay'
    
    @classmethod
    def process_webhook_confirmation(cls, gateway_transaction, webhook_payload):
        """
        Process webhook from gateway - SOURCE OF TRUTH.
        
        POLICY: Webhooks are authoritative. Local/client state is non-authoritative.
        All webhook processing must be idempotent.
        """
        try:
            if not isinstance(gateway_transaction.webhook_data, list):
                gateway_transaction.webhook_data = []
            
            gateway_transaction.webhook_data.append({
                'timestamp': timezone.now().isoformat(),
                'payload': webhook_payload,
            })
            
            status = webhook_payload.get('status', '').lower()
            
            with transaction.atomic():
                if status in ['approved', 'completed', 'success']:
                    gateway_transaction.status = 'approved'
                    gateway_transaction.approved_at = timezone.now()
                    
                    for service_tx in gateway_transaction.service_transactions.all():
                        service_tx.status = 'completed'
                        service_tx.completed_at = timezone.now()
                        service_tx.save()
                        
                        service_tx.fee_details.fee_collected = True
                        service_tx.fee_details.collected_at = timezone.now()
                        service_tx.fee_details.save()
                        
                        cls._generate_invoice(service_tx)
                    
                    logger.info(f"Payment confirmed via webhook: {gateway_transaction.gateway_reference}")
                    
                elif status in ['declined', 'failed']:
                    gateway_transaction.status = 'declined'
                    gateway_transaction.declined_at = timezone.now()
                    gateway_transaction.last_error_message = webhook_payload.get('message', 'Payment declined')
                    
                    for service_tx in gateway_transaction.service_transactions.all():
                        service_tx.status = 'failed'
                        service_tx.failed_at = timezone.now()
                        service_tx.save()
                    
                    logger.warning(f"Payment declined via webhook: {gateway_transaction.gateway_reference}")
                
                gateway_transaction.save()
                
        except Exception as e:
            logger.error(f"Failed to process webhook: {e}")
            raise
    
    @classmethod
    def _generate_invoice(cls, service_transaction):
        """
        Generate invoice after successful payment.
        
        POLICY: Every payment must have an invoice linking:
        - Patient & Provider
        - Service details
        - Dual currency amounts
        - Tax & commission breakdown
        - Gateway transaction reference
        """
        try:
            fee_details = service_transaction.fee_details
            
            receipt = PaymentReceipt.objects.create(
                service_transaction=service_transaction,
                receipt_number=f"RCP-{service_transaction.transaction_ref}",
                transaction_type=service_transaction.service_type.upper(),
                payment_status='PAID',
                
                issued_to=service_transaction.patient,
                issued_by=service_transaction.service_provider,
                
                subtotal=service_transaction.amount_local,
                tax_amount=fee_details.tax_amount_local,
                platform_fee=fee_details.platform_fee_amount_local,
                total_amount=service_transaction.amount_local,
                currency=service_transaction.currency_code,
                
                payment_method=service_transaction.payment_method,
                gateway_transaction_id=str(service_transaction.gateway_transaction.id) if service_transaction.gateway_transaction else '',
                
                service_details={
                    'amount_usd': str(service_transaction.amount_usd),
                    'amount_local': str(service_transaction.amount_local),
                    'currency': service_transaction.currency_code,
                    'exchange_rate': str(service_transaction.exchange_rate_used),
                    'commission_usd': str(fee_details.platform_fee_amount_usd),
                    'commission_local': str(fee_details.platform_fee_amount_local),
                    'tax_usd': str(fee_details.tax_amount_usd),
                    'tax_local': str(fee_details.tax_amount_local),
                },
                
                billing_date=service_transaction.created_at,
                payment_date=service_transaction.completed_at,
                issued_at=timezone.now(),
            )
            
            receipt.ensure_invoice_data()
            
            logger.info(f"Invoice generated: {receipt.invoice_number}")
            return receipt
            
        except Exception as e:
            logger.error(f"Failed to generate invoice: {e}")
