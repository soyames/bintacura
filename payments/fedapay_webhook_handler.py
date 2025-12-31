import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import (
    FedaPayCustomer,
    FedaPayTransaction,
    FedaPayPayout,
    FedaPayWebhookEvent
)
from core.models import Participant, Wallet, Transaction as CoreTransaction
from .fedapay_service import fedapay_service

logger = logging.getLogger(__name__)


class FedaPayWebhookHandler:
    """Handle FedaPay webhook events"""
    
    @staticmethod
    @transaction.atomic
    def handle_webhook(event_data: dict) -> bool:
        """
        Process incoming webhook event with idempotency guarantee.

        ACID Compliance:
        - Wrapped in @transaction.atomic for full ACID guarantees
        - Uses select_for_update() with get_or_create to prevent race conditions
        - Returns immediately if event already processed
        - Ensures each webhook is processed exactly once
        """
        event_type = event_data.get('type')
        entity = event_data.get('entity', {})
        event_id = event_data.get('id')

        # IDEMPOTENCY: Use get_or_create with select_for_update to prevent duplicate processing
        webhook_event, created = FedaPayWebhookEvent.objects.select_for_update().get_or_create(
            event_id=event_id,
            defaults={
                'event_type': event_type,
                'payload': event_data
            }
        )

        # If event already exists and was processed, return success (idempotent)
        if not created:
            if webhook_event.processed:
                logger.info(f"Webhook event {event_id} already processed. Returning success (idempotent).")
                return True
            else:
                logger.warning(f"Webhook event {event_id} exists but failed previous processing. Retrying...")
        
        try:
            if event_type == 'transaction.approved':
                FedaPayWebhookHandler._handle_transaction_approved(entity, webhook_event)
                FedaPayWebhookHandler._handle_gateway_transaction_approved(entity, webhook_event)
            elif event_type == 'transaction.canceled':
                FedaPayWebhookHandler._handle_transaction_canceled(entity, webhook_event)
                FedaPayWebhookHandler._handle_gateway_transaction_canceled(entity, webhook_event)
            elif event_type == 'transaction.declined':
                FedaPayWebhookHandler._handle_transaction_declined(entity, webhook_event)
                FedaPayWebhookHandler._handle_gateway_transaction_declined(entity, webhook_event)
            elif event_type == 'transaction.refunded':
                FedaPayWebhookHandler._handle_transaction_refunded(entity, webhook_event)
            elif event_type == 'payout.sent':
                FedaPayWebhookHandler._handle_payout_sent(entity, webhook_event)
            elif event_type == 'payout.failed':
                FedaPayWebhookHandler._handle_payout_failed(entity, webhook_event)
            else:
                logger.warning(f"Unknown webhook event type: {event_type}")
            
            webhook_event.processed = True
            webhook_event.processed_at = timezone.now()
            webhook_event.save()
            return True
            
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            webhook_event.processing_error = str(e)
            webhook_event.save()
            return False
    
    @staticmethod
    @transaction.atomic
    def _handle_transaction_approved(entity: dict, webhook_event):
        """Handle approved transaction - credit user wallet (NO FEES on wallet top-up)"""
        fedapay_txn_id = entity.get('id')
        
        try:
            fedapay_txn = FedaPayTransaction.objects.get(fedapay_transaction_id=fedapay_txn_id)
        except FedaPayTransaction.DoesNotExist:
            logger.error(f"FedaPay transaction {fedapay_txn_id} not found")
            return
        
        if fedapay_txn.status == 'approved':
            logger.info(f"Transaction {fedapay_txn_id} already approved")
            return
        
        # Update FedaPay transaction
        fedapay_txn.status = 'approved'
        fedapay_txn.approved_at = timezone.now()
        
        # FedaPay fees (charged by FedaPay, not us)
        fedapay_gateway_fees = Decimal(str(entity.get('fees', 0))) / 100
        fedapay_txn.fees = fedapay_gateway_fees
        fedapay_txn.commission = Decimal(str(entity.get('commission', 0))) / 100
        fedapay_txn.amount_transferred = Decimal(str(entity.get('amount_transferred', 0))) / 100
        fedapay_txn.receipt_url = entity.get('receipt_url', '')
        fedapay_txn.save()
        
        webhook_event.fedapay_transaction = fedapay_txn
        
        # For wallet top-ups, credit the user's wallet with FULL amount (no BINTACURA fees)
        if fedapay_txn.transaction_type == 'wallet_topup':
            wallet = Wallet.objects.select_for_update().get(participant=fedapay_txn.participant)
            
            # Create core transaction - NO BINTACURA FEES ON TOP-UPS
            balance_before = wallet.balance
            # Credit full amount to wallet
            balance_after = balance_before + fedapay_txn.amount
            
            core_txn = CoreTransaction.objects.create(
                transaction_ref=f"FEDAPAY-{fedapay_txn.fedapay_reference}",
                wallet=wallet,
                transaction_type='deposit',
                amount=fedapay_txn.amount,
                currency=fedapay_txn.currency,
                status='completed',
                payment_method='mobile_money',
                description=f"Wallet top-up via FedaPay - {fedapay_txn.description}",
                balance_before=balance_before,
                balance_after=balance_after,
                completed_at=timezone.now(),
                metadata={
                    'fedapay_transaction_id': fedapay_txn_id,
                    'fedapay_reference': fedapay_txn.fedapay_reference,
                    'fedapay_gateway_fees': str(fedapay_gateway_fees),
                    'BINTACURA_platform_fee': '0.00',  # NO FEES ON TOP-UP
                    'note': 'BINTACURA does not charge fees on wallet top-ups'
                }
            )
            
            # Update wallet balance - full amount credited
            wallet.balance = balance_after
            wallet.last_transaction_date = timezone.now()
            wallet.save()
            
            # Link transactions
            fedapay_txn.core_transaction = core_txn
            fedapay_txn.save()
            
            logger.info(f"Wallet credited (NO FEES): {fedapay_txn.amount} {fedapay_txn.currency} for user {fedapay_txn.participant.email}")
    
    @staticmethod
    @transaction.atomic
    def _handle_transaction_canceled(entity: dict, webhook_event):
        """Handle canceled transaction"""
        fedapay_txn_id = entity.get('id')
        
        try:
            fedapay_txn = FedaPayTransaction.objects.get(fedapay_transaction_id=fedapay_txn_id)
            fedapay_txn.status = 'canceled'
            fedapay_txn.canceled_at = timezone.now()
            fedapay_txn.save()
            
            webhook_event.fedapay_transaction = fedapay_txn
            
            logger.info(f"Transaction {fedapay_txn_id} canceled")
        except FedaPayTransaction.DoesNotExist:
            logger.error(f"FedaPay transaction {fedapay_txn_id} not found")
    
    @staticmethod
    @transaction.atomic
    def _handle_transaction_declined(entity: dict, webhook_event):
        """Handle declined transaction"""
        fedapay_txn_id = entity.get('id')
        
        try:
            fedapay_txn = FedaPayTransaction.objects.get(fedapay_transaction_id=fedapay_txn_id)
            fedapay_txn.status = 'declined'
            fedapay_txn.declined_at = timezone.now()
            fedapay_txn.last_error_code = entity.get('last_error_code', '')
            fedapay_txn.save()
            
            webhook_event.fedapay_transaction = fedapay_txn
            
            logger.info(f"Transaction {fedapay_txn_id} declined")
        except FedaPayTransaction.DoesNotExist:
            logger.error(f"FedaPay transaction {fedapay_txn_id} not found")
    
    @staticmethod
    @transaction.atomic
    def _handle_transaction_refunded(entity: dict, webhook_event):
        """Handle refunded transaction - debit user wallet"""
        fedapay_txn_id = entity.get('id')
        
        try:
            fedapay_txn = FedaPayTransaction.objects.get(fedapay_transaction_id=fedapay_txn_id)
            fedapay_txn.status = 'refunded'
            fedapay_txn.refunded_at = timezone.now()
            fedapay_txn.save()
            
            webhook_event.fedapay_transaction = fedapay_txn
            
            # If this was a wallet top-up, debit the wallet
            if fedapay_txn.transaction_type == 'wallet_topup' and fedapay_txn.core_transaction:
                wallet = Wallet.objects.select_for_update().get(participant=fedapay_txn.participant)
                
                balance_before = wallet.balance
                balance_after = balance_before - fedapay_txn.amount
                
                # Create refund transaction
                CoreTransaction.objects.create(
                    transaction_ref=f"REFUND-{fedapay_txn.fedapay_reference}",
                    wallet=wallet,
                    transaction_type='refund',
                    amount=fedapay_txn.amount,
                    currency=fedapay_txn.currency,
                    status='completed',
                    payment_method='mobile_money',
                    description=f"Refund for FedaPay transaction - {fedapay_txn.description}",
                    balance_before=balance_before,
                    balance_after=balance_after,
                    completed_at=timezone.now(),
                    metadata={
                        'original_fedapay_transaction_id': fedapay_txn_id,
                        'original_fedapay_reference': fedapay_txn.fedapay_reference
                    }
                )
                
                # Update wallet balance
                wallet.balance = balance_after
                wallet.last_transaction_date = timezone.now()
                wallet.save()
                
                logger.info(f"Wallet debited for refund: {fedapay_txn.amount} {fedapay_txn.currency}")
        except FedaPayTransaction.DoesNotExist:
            logger.error(f"FedaPay transaction {fedapay_txn_id} not found")
    
    @staticmethod
    @transaction.atomic
    def _handle_payout_sent(entity: dict, webhook_event):
        """Handle successful payout"""
        fedapay_payout_id = entity.get('id')
        
        try:
            fedapay_payout = FedaPayPayout.objects.get(fedapay_payout_id=fedapay_payout_id)
            fedapay_payout.status = 'sent'
            fedapay_payout.sent_at = timezone.now()
            fedapay_payout.amount_transferred = Decimal(str(entity.get('amount_transferred', 0))) / 100
            fedapay_payout.fees = Decimal(str(entity.get('fees', 0))) / 100
            fedapay_payout.commission = Decimal(str(entity.get('commission', 0))) / 100
            fedapay_payout.save()
            
            webhook_event.fedapay_payout = fedapay_payout
            
            # Update provider payout status
            if fedapay_payout.provider_payout:
                fedapay_payout.provider_payout.status = 'completed'
                fedapay_payout.provider_payout.processed_at = timezone.now()
                fedapay_payout.provider_payout.save()
            
            # Handle refund completion if this is a refund payout
            if 'refund_request_id' in fedapay_payout.custom_metadata:
                from core.refund_webhook_service import RefundWebhookService
                RefundWebhookService.complete_refund_on_webhook(fedapay_payout)
            
            logger.info(f"Payout {fedapay_payout_id} sent successfully")
        except FedaPayPayout.DoesNotExist:
            logger.error(f"FedaPay payout {fedapay_payout_id} not found")
    
    @staticmethod
    @transaction.atomic
    def _handle_payout_failed(entity: dict, webhook_event):
        """Handle failed payout"""
        fedapay_payout_id = entity.get('id')
        
        try:
            fedapay_payout = FedaPayPayout.objects.get(fedapay_payout_id=fedapay_payout_id)
            fedapay_payout.status = 'failed'
            fedapay_payout.failed_at = timezone.now()
            fedapay_payout.last_error_code = entity.get('last_error_code', '')
            fedapay_payout.save()
            
            webhook_event.fedapay_payout = fedapay_payout
            
            # Update provider payout status
            if fedapay_payout.provider_payout:
                fedapay_payout.provider_payout.status = 'failed'
                fedapay_payout.provider_payout.save()
            
            # Handle refund failure if this is a refund payout
            if 'refund_request_id' in fedapay_payout.custom_metadata:
                from core.refund_webhook_service import RefundWebhookService
                RefundWebhookService.fail_refund_on_webhook(fedapay_payout)
            
            logger.info(f"Payout {fedapay_payout_id} failed")
        except FedaPayPayout.DoesNotExist:
            logger.error(f"FedaPay payout {fedapay_payout_id} not found")
    
    @staticmethod
    @transaction.atomic
    def _handle_gateway_transaction_approved(entity: dict, webhook_event):
        """Handle approved gateway transaction for service payments"""
        from .models import GatewayTransaction, ServiceTransaction, PaymentReceipt
        from .enhanced_receipt_service import EnhancedReceiptService
        
        fedapay_txn_id = str(entity.get('id'))
        
        try:
            gateway_txn = GatewayTransaction.objects.get(gateway_transaction_id=fedapay_txn_id)
        except GatewayTransaction.DoesNotExist:
            logger.info(f"No GatewayTransaction found for FedaPay transaction {fedapay_txn_id}")
            return
        
        if gateway_txn.status == 'approved':
            logger.info(f"GatewayTransaction {gateway_txn.id} already approved")
            return
        
        gateway_txn.status = 'approved'
        gateway_txn.approved_at = timezone.now()
        gateway_txn.fees = Decimal(str(entity.get('fees', 0))) / 100
        gateway_txn.commission = Decimal(str(entity.get('commission', 0))) / 100
        gateway_txn.amount_transferred = Decimal(str(entity.get('amount_transferred', 0))) / 100
        gateway_txn.webhook_data.append(entity)
        gateway_txn.save()
        
        service_txns = ServiceTransaction.objects.filter(gateway_transaction=gateway_txn)
        for service_txn in service_txns:
            service_txn.status = 'completed'
            service_txn.completed_at = timezone.now()
            service_txn.save()

            if not hasattr(service_txn, 'receipt'):
                receipt = EnhancedReceiptService.create_receipt_from_service_transaction(service_txn)
                logger.info(f"Receipt {receipt.receipt_number} created for service transaction {service_txn.id}")

        # Handle pharmacy order payments
        if gateway_txn.transaction_type == 'pharmacy_order':
            FedaPayWebhookHandler._handle_pharmacy_order_payment(gateway_txn)

        logger.info(f"Gateway transaction {gateway_txn.id} approved and receipt generated")
    
    @staticmethod
    @transaction.atomic
    def _handle_gateway_transaction_canceled(entity: dict, webhook_event):
        """Handle canceled gateway transaction"""
        from .models import GatewayTransaction, ServiceTransaction
        
        fedapay_txn_id = str(entity.get('id'))
        
        try:
            gateway_txn = GatewayTransaction.objects.get(gateway_transaction_id=fedapay_txn_id)
            gateway_txn.status = 'cancelled'
            gateway_txn.webhook_data.append(entity)
            gateway_txn.save()
            
            ServiceTransaction.objects.filter(gateway_transaction=gateway_txn).update(
                status='cancelled',
                cancelled_at=timezone.now()
            )
            
            logger.info(f"Gateway transaction {gateway_txn.id} canceled")
        except GatewayTransaction.DoesNotExist:
            logger.info(f"No GatewayTransaction found for FedaPay transaction {fedapay_txn_id}")
    
    @staticmethod
    @transaction.atomic
    def _handle_gateway_transaction_declined(entity: dict, webhook_event):
        """Handle declined gateway transaction"""
        from .models import GatewayTransaction, ServiceTransaction
        
        fedapay_txn_id = str(entity.get('id'))
        
        try:
            gateway_txn = GatewayTransaction.objects.get(gateway_transaction_id=fedapay_txn_id)
            gateway_txn.status = 'declined'
            gateway_txn.declined_at = timezone.now()
            gateway_txn.last_error_code = entity.get('last_error_code', '')
            gateway_txn.last_error_message = entity.get('last_error_message', '')
            gateway_txn.webhook_data.append(entity)
            gateway_txn.save()
            
            ServiceTransaction.objects.filter(gateway_transaction=gateway_txn).update(
                status='failed',
                failed_at=timezone.now()
            )
            
            logger.info(f"Gateway transaction {gateway_txn.id} declined")
        except GatewayTransaction.DoesNotExist:
            logger.info(f"No GatewayTransaction found for FedaPay transaction {fedapay_txn_id}")

    @staticmethod
    @transaction.atomic
    def _handle_pharmacy_order_payment(gateway_txn):
        """Handle approved pharmacy order payment"""
        try:
            from pharmacy.models import PharmacyOrder
            from pharmacy.payment_service import PharmacyPaymentService
            from core.models import Notification

            # Get order from gateway transaction reference
            order_id = gateway_txn.metadata.get('order_id') or gateway_txn.reference_id
            if not order_id:
                logger.warning(f"No order_id in gateway transaction {gateway_txn.id}")
                return

            order = PharmacyOrder.objects.select_for_update().filter(id=order_id).first()
            if not order:
                logger.error(f"PharmacyOrder {order_id} not found")
                return

            if order.payment_status == 'paid':
                logger.info(f"PharmacyOrder {order.order_number} already paid")
                return

            # Update order
            order.payment_status = 'paid'
            order.amount_paid = order.total_amount
            order.payment_reference = f"FEDAPAY-{gateway_txn.gateway_transaction_id}"
            order.save()

            # Create receipt
            try:
                receipt = PharmacyPaymentService.create_payment_receipt(order)
                logger.info(f"Receipt {receipt.receipt_number} created for order {order.order_number}")
            except Exception as receipt_error:
                logger.error(f"Failed to create receipt for order {order.order_number}: {receipt_error}")

            # Notify patient
            try:
                Notification.objects.create(
                    participant=order.patient,
                    title='Paiement Confirmé',
                    message=f'Votre paiement pour la commande {order.order_number} a été confirmé.',
                    notification_type='payment',
                    priority='high'
                )
            except Exception:
                pass

            # Notify pharmacy
            try:
                Notification.objects.create(
                    participant=order.pharmacy,
                    title='Paiement Reçu',
                    message=f'Paiement reçu pour la commande {order.order_number} de {order.patient.full_name}.',
                    notification_type='payment',
                    priority='high'
                )
            except Exception:
                pass

            logger.info(f"PharmacyOrder {order.order_number} payment processed successfully")

        except Exception as e:
            logger.error(f"Error handling pharmacy order payment: {e}", exc_info=True)


class FedaPayWalletService:
    """Service for wallet operations with FedaPay"""
    
    @staticmethod
    @transaction.atomic
    def initiate_wallet_topup(participant: Participant, amount: Decimal, currency: str, callback_url: str) -> dict:
        """Initiate wallet top-up via FedaPay"""
        
        # Get or create FedaPay customer
        try:
            fedapay_customer = FedaPayCustomer.objects.get(participant=participant)
        except FedaPayCustomer.DoesNotExist:
            customer_data = fedapay_service.create_customer(participant)
            fedapay_customer = FedaPayCustomer.objects.create(
                participant=participant,
                fedapay_customer_id=customer_data['id'],
                email=customer_data['email'],
                phone_number=customer_data.get('phone_number', {}).get('number', '')
            )
        
        # Create transaction
        description = f"BINTACURA wallet top-up - {amount} {currency}"
        
        txn_data = fedapay_service.create_transaction(
            amount=amount,
            currency=currency,
            description=description,
            customer_id=fedapay_customer.fedapay_customer_id,
            callback_url=callback_url,
            custom_metadata={
                'participant_id': str(participant.uid),
                'transaction_type': 'wallet_topup'
            }
        )
        
        # Generate payment token
        token_data = fedapay_service.generate_payment_token(txn_data['id'])
        
        # Store in database
        fedapay_txn = FedaPayTransaction.objects.create(
            fedapay_transaction_id=txn_data['id'],
            fedapay_reference=txn_data['reference'],
            participant=participant,
            fedapay_customer=fedapay_customer,
            transaction_type='wallet_topup',
            amount=amount,
            currency=currency,
            description=description,
            payment_token=token_data.get('token', ''),
            payment_url=token_data.get('url', ''),
            callback_url=callback_url,
            custom_metadata={
                'participant_id': str(participant.uid)
            }
        )
        
        return {
            'transaction_id': str(fedapay_txn.id),
            'fedapay_transaction_id': txn_data['id'],
            'payment_url': token_data.get('url', ''),
            'payment_token': token_data.get('token', ''),
            'amount': amount,
            'currency': currency
        }
    
    @staticmethod
    def get_transaction_status(fedapay_transaction_id: int) -> dict:
        """Get status of a FedaPay transaction"""
        return fedapay_service.get_transaction(fedapay_transaction_id)

