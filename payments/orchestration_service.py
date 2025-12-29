from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from core.models import Participant, Transaction
from currency_converter.services import CurrencyConverterService
import logging

logger = logging.getLogger(__name__)


class PaymentOrchestrationService:
    """
    Central service for orchestrating payments according to Final Payment Model.
    All payments go through external gateways with 1% BintaCura commission.
    No money is stored - only ledger records.
    """
    
    BINTACURA_COMMISSION_RATE = Decimal("0.01")  # 1%
    TAX_RATE = Decimal("0.18")  # 18% where applicable
    
    @staticmethod
    def resolve_participant_currency(participant):
        """
        Resolve participant's local currency using phone country code + geolocation.
        Returns: (currency_code, country_code, resolution_method)
        """
        currency_code = "USD"  # Default fallback
        country_code = None
        resolution_method = "default"
        
        try:
            # Primary: Phone number country code
            phone_country = None
            if participant.phone_number:
                # Extract country code from phone number
                phone_country = CurrencyConverterService.get_country_from_phone(participant.phone_number)
            
            # Secondary: Geolocation
            geo_country = None
            if participant.longitude and participant.latitude:
                geo_country = CurrencyConverterService.get_country_from_coordinates(
                    participant.longitude, 
                    participant.latitude
                )
            
            # Resolution logic
            if phone_country and geo_country:
                if phone_country == geo_country:
                    country_code = phone_country
                    resolution_method = "combined"
                else:
                    # Geolocation takes precedence
                    country_code = geo_country
                    resolution_method = "geo_priority"
                    logger.warning(
                        f"Currency mismatch for {participant.email}: "
                        f"phone={phone_country}, geo={geo_country}. Using geo."
                    )
            elif phone_country:
                country_code = phone_country
                resolution_method = "phone"
            elif geo_country:
                country_code = geo_country
                resolution_method = "geo"
            
            if country_code:
                currency_code = CurrencyConverterService.get_currency_for_country(country_code)
        
        except Exception as e:
            logger.error(f"Error resolving currency for {participant.email}: {e}")
            currency_code = "USD"
            resolution_method = "error_fallback"
        
        return currency_code, country_code, resolution_method
    
    @staticmethod
    @transaction.atomic
    def initiate_payment(
        payer_participant,
        payee_participant,
        amount_usd,
        payment_context="patient_service",
        description="",
        apply_tax=False,
        metadata=None
    ):
        """
        Initiate a payment through external gateway with commission split.
        
        Args:
            payer_participant: Participant making payment
            payee_participant: Participant receiving payment
            amount_usd: Amount in USD (reference currency)
            payment_context: patient_service/b2b_supplier/payroll
            description: Payment description
            apply_tax: Whether to apply 18% tax
            metadata: Additional metadata
        
        Returns:
            dict with payment details and gateway info
        """
        amount_usd = Decimal(str(amount_usd))
        
        # Resolve payer's local currency
        currency_code, country_code, resolution_method = PaymentOrchestrationService.resolve_participant_currency(
            payer_participant
        )
        
        # Convert USD to local currency
        conversion_result = CurrencyConverterService.convert(
            amount_usd,
            "USD",
            currency_code
        )
        
        amount_local = conversion_result['converted_amount']
        exchange_rate = conversion_result['rate']
        
        # Calculate commission (1%)
        commission_usd = amount_usd * PaymentOrchestrationService.BINTACURA_COMMISSION_RATE
        commission_local = amount_local * PaymentOrchestrationService.BINTACURA_COMMISSION_RATE
        
        # Calculate tax if applicable
        tax_amount = Decimal("0")
        if apply_tax:
            tax_amount = amount_local * PaymentOrchestrationService.TAX_RATE
        
        # Total amount including tax
        total_local = amount_local + tax_amount
        
        # Create Transaction record (ledger entry)
        txn = Transaction.objects.create(
            transaction_type="payment",
            sender=payer_participant,
            recipient=payee_participant,
            
            # Dual currency
            amount_usd=amount_usd,
            amount_local=amount_local,
            currency_code=currency_code,
            exchange_rate_used=exchange_rate,
            conversion_timestamp=timezone.now(),
            
            # Commission
            commission_amount_usd=commission_usd,
            commission_amount_local=commission_local,
            tax_amount=tax_amount,
            
            # Currency resolution audit
            resolved_country=country_code,
            resolution_method=resolution_method,
            
            # Context
            payment_context=payment_context,
            description=description,
            
            # Legacy fields (for compatibility)
            amount=amount_local,
            currency=currency_code,
            balance_before=0,  # Not used in ledger model
            balance_after=0,   # Not used in ledger model
            
            # Status
            status="pending",
            
            # Metadata
            metadata=metadata or {},
        )
        
        logger.info(
            f"Payment initiated: {txn.transaction_ref} | "
            f"Payer={payer_participant.email} | "
            f"Payee={payee_participant.email} | "
            f"Amount={amount_usd} USD ({amount_local} {currency_code})"
        )
        
        return {
            "transaction_ref": txn.transaction_ref,
            "transaction_id": str(txn.id),
            "amount_usd": float(amount_usd),
            "amount_local": float(total_local),
            "currency_code": currency_code,
            "commission_local": float(commission_local),
            "tax_amount": float(tax_amount),
            "total_local": float(total_local),
            "exchange_rate": float(exchange_rate),
            "status": "pending",
            "next_step": "gateway_payment",
        }
    
    @staticmethod
    @transaction.atomic
    def record_gateway_response(transaction_ref, gateway_data):
        """
        Record gateway transaction response (called after gateway returns).
        
        Args:
            transaction_ref: BintaCura transaction reference
            gateway_data: dict with gateway response data
        """
        try:
            txn = Transaction.objects.get(transaction_ref=transaction_ref)
            
            txn.gateway_transaction_id = gateway_data.get('transaction_id')
            txn.gateway_reference = gateway_data.get('reference')
            txn.gateway_name = gateway_data.get('gateway_name', 'fedapay')
            txn.status = gateway_data.get('status', 'processing')
            
            if gateway_data.get('status') == 'completed':
                txn.completed_at = timezone.now()
            
            txn.metadata.update({
                'gateway_response': gateway_data,
                'gateway_updated_at': timezone.now().isoformat(),
            })
            
            txn.save()
            
            logger.info(f"Gateway response recorded for {transaction_ref}: {gateway_data.get('status')}")
            
            return True
        except Transaction.DoesNotExist:
            logger.error(f"Transaction not found: {transaction_ref}")
            return False
        except Exception as e:
            logger.error(f"Error recording gateway response: {e}")
            return False
    
    @staticmethod
    @transaction.atomic
    def process_webhook(webhook_payload):
        """
        Process webhook from payment gateway (source of truth).
        
        Args:
            webhook_payload: Full webhook data from gateway
        """
        try:
            # Extract transaction reference from webhook
            transaction_ref = webhook_payload.get('custom_metadata', {}).get('transaction_ref')
            
            if not transaction_ref:
                logger.error("No transaction_ref in webhook payload")
                return False
            
            txn = Transaction.objects.get(transaction_ref=transaction_ref)
            
            # Update from webhook (AUTHORITATIVE)
            txn.gateway_transaction_id = webhook_payload.get('id')
            txn.gateway_reference = webhook_payload.get('reference')
            txn.status = webhook_payload.get('status', 'processing')
            txn.webhook_payload = webhook_payload
            txn.webhook_received_at = timezone.now()
            
            if webhook_payload.get('status') == 'approved':
                txn.status = 'completed'
                txn.completed_at = timezone.now()
            elif webhook_payload.get('status') in ['declined', 'failed']:
                txn.status = 'failed'
            
            txn.save()
            
            logger.info(
                f"Webhook processed for {transaction_ref}: {txn.status}"
            )
            
            return True
        
        except Transaction.DoesNotExist:
            logger.error(f"Transaction not found for webhook: {transaction_ref}")
            return False
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return False
    
    @staticmethod
    def get_participant_ledger_balance(participant, currency_code="USD"):
        """
        Get computed ledger balance for participant (no stored balance).
        
        Args:
            participant: Participant instance
            currency_code: Currency to return balance in
        
        Returns:
            Decimal balance
        """
        from django.db.models import Sum, Q
        
        # Received (completed transactions)
        received = Transaction.objects.filter(
            recipient=participant,
            status="completed"
        ).aggregate(
            total_usd=Sum('amount_usd'),
            total_local=Sum('amount_local')
        )
        
        # Sent (completed transactions)
        sent = Transaction.objects.filter(
            sender=participant,
            status="completed"
        ).aggregate(
            total_usd=Sum('amount_usd'),
            total_local=Sum('amount_local')
        )
        
        received_usd = received['total_usd'] or Decimal("0")
        sent_usd = sent['total_usd'] or Decimal("0")
        
        balance_usd = received_usd - sent_usd
        
        # Convert to requested currency if not USD
        if currency_code != "USD":
            conversion = CurrencyConverterService.convert(balance_usd, "USD", currency_code)
            return conversion['converted_amount']
        
        return balance_usd
