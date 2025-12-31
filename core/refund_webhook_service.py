import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import RefundRequest, Transaction, Wallet, ParticipantActivityLog, AuditLogEntry
from payments.fedapay_service import fedapay_service
from payments.models import FedaPayPayout

logger = logging.getLogger(__name__)


class RefundWebhookService:
    """
    Service to handle refund processing with payment gateway webhook integration.
    Ensures ACID compliance and prevents duplicate refunds.
    """
    
    @staticmethod
    @transaction.atomic
    def process_refund_via_gateway(refund_request: RefundRequest, admin_participant) -> dict:
        """
        Process refund by initiating payout through payment gateway (FedaPay).
        This creates a payout to patient's mobile money account.
        
        ACID Compliance:
        - Wrapped in @transaction.atomic
        - Uses select_for_update() for locking
        - Idempotency guaranteed via status checks
        """
        # Lock the refund request
        refund_request = RefundRequest.objects.select_for_update().get(id=refund_request.id)
        
        # Validate current status
        if refund_request.status != 'pending':
            raise ValueError(f"Refund request is not pending. Current status: {refund_request.status}")
        
        # Validate patient role
        if refund_request.participant.role != 'patient':
            raise ValueError("Only patient refund requests can be processed")
        
        # Check for duplicate refunds on same transaction
        if refund_request.transaction:
            existing_refunds = RefundRequest.objects.filter(
                transaction=refund_request.transaction,
                status__in=['completed', 'processing']
            ).exclude(id=refund_request.id)
            
            if existing_refunds.exists():
                raise ValueError("A refund for this transaction is already being processed or completed")
            
            # Validate refund amount excludes transaction fees
            max_refundable = refund_request.get_max_refundable_amount()
            if refund_request.amount > max_refundable:
                raise ValueError(f"Refund amount {refund_request.amount} exceeds maximum refundable amount {max_refundable} (transaction fees excluded)")
        
        # Check insurance claim conflicts
        if refund_request.insurance_claim:
            if refund_request.insurance_claim.status == 'paid':
                raise ValueError("Cannot refund - insurance claim already paid")
        
        # Update status to processing
        refund_request.status = 'processing'
        refund_request.admin_reviewer = admin_participant
        refund_request.reviewed_at = timezone.now()
        refund_request.save()
        
        try:
            # Get patient's phone number for mobile money payout
            patient = refund_request.participant
            phone_number = patient.phone_number
            
            if not phone_number:
                raise ValueError("Patient does not have a phone number registered for mobile money payout")
            
            # Initiate FedaPay payout
            # NOTE: Refund amount already excludes transaction fees (validated in get_max_refundable_amount)
            # Patients are refunded the net amount they paid, not including gateway processing fees
            payout_data = fedapay_service.create_payout(
                amount=refund_request.amount,
                currency=refund_request.currency,
                phone_number=phone_number,
                description=f"Refund for request {refund_request.id}: {refund_request.reason}",
                custom_metadata={
                    'refund_request_id': str(refund_request.id),
                    'participant_id': str(patient.uid),
                    'refund_type': refund_request.request_type
                }
            )
            
            # Store FedaPay payout record
            fedapay_payout = FedaPayPayout.objects.create(
                fedapay_payout_id=payout_data['id'],
                fedapay_reference=payout_data.get('reference', ''),
                participant=patient,
                amount=refund_request.amount,
                currency=refund_request.currency,
                recipient_phone=phone_number,
                description=f"Refund for request {refund_request.id}",
                status='pending',
                custom_metadata={
                    'refund_request_id': str(refund_request.id)
                }
            )
            
            # Link payout to refund request
            refund_request.metadata = refund_request.metadata or {}
            refund_request.metadata['fedapay_payout_id'] = str(fedapay_payout.id)
            refund_request.metadata['fedapay_reference'] = payout_data.get('reference', '')
            refund_request.save()
            
            # Log activity
            ParticipantActivityLog.objects.create(
                participant=patient,
                activity_type="refund_processing",
                description=f"Refund of {refund_request.amount} {refund_request.currency} initiated via FedaPay",
            )
            
            AuditLogEntry.objects.create(
                participant=admin_participant,
                action_type="create",
                resource_type="fedapay_payout",
                resource_id=str(fedapay_payout.id),
                details={
                    "action": "initiate_refund_payout",
                    "refund_request_id": str(refund_request.id),
                    "amount": float(refund_request.amount),
                    "currency": refund_request.currency,
                    "patient_email": patient.email,
                },
            )
            
            return {
                'success': True,
                'refund_request': refund_request,
                'fedapay_payout': fedapay_payout,
                'message': 'Refund payout initiated. Will be completed when webhook confirms.'
            }
            
        except Exception as e:
            # Rollback status on failure
            refund_request.status = 'pending'
            refund_request.admin_reviewer = None
            refund_request.reviewed_at = None
            refund_request.save()
            
            logger.error(f"Failed to initiate refund payout for request {refund_request.id}: {e}")
            raise
    
    @staticmethod
    @transaction.atomic
    def complete_refund_on_webhook(fedapay_payout: FedaPayPayout) -> None:
        """
        Called by webhook handler when payout is confirmed as 'sent'.
        Completes the refund request and creates transaction record.
        """
        # Get refund request
        refund_request_id = fedapay_payout.custom_metadata.get('refund_request_id')
        if not refund_request_id:
            logger.warning(f"No refund_request_id in FedaPay payout {fedapay_payout.id}")
            return
        
        try:
            refund_request = RefundRequest.objects.select_for_update().get(id=refund_request_id)
        except RefundRequest.DoesNotExist:
            logger.error(f"RefundRequest {refund_request_id} not found")
            return
        
        if refund_request.status == 'completed':
            logger.info(f"RefundRequest {refund_request_id} already completed")
            return
        
        # Get or create wallet
        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            participant=refund_request.participant,
            defaults={'currency': refund_request.currency, 'balance': Decimal('0.00')}
        )
        
        # Create refund transaction record
        balance_before = wallet.balance
        balance_after = balance_before + refund_request.amount
        
        refund_txn = Transaction.objects.create(
            transaction_ref=f"REFUND-{refund_request.id}",
            wallet=wallet,
            transaction_type='refund',
            amount=refund_request.amount,
            currency=refund_request.currency,
            status='completed',
            payment_method='mobile_money',
            description=f"Refund via FedaPay: {refund_request.reason}",
            balance_before=balance_before,
            balance_after=balance_after,
            completed_at=timezone.now(),
            metadata={
                'refund_request_id': str(refund_request.id),
                'fedapay_payout_id': str(fedapay_payout.id),
                'fedapay_reference': fedapay_payout.fedapay_reference,
                'refund_type': refund_request.request_type
            }
        )
        
        # Update wallet balance (credit patient)
        wallet.balance = balance_after
        wallet.last_transaction_date = timezone.now()
        wallet.save()
        
        # Complete refund request
        refund_request.status = 'completed'
        refund_request.refund_transaction = refund_txn
        refund_request.processed_at = timezone.now()
        refund_request.save()
        
        # Log completion
        ParticipantActivityLog.objects.create(
            participant=refund_request.participant,
            activity_type="refund_completed",
            description=f"Refund of {refund_request.amount} {refund_request.currency} completed successfully",
        )
        
        logger.info(f"RefundRequest {refund_request.id} completed successfully via webhook")
    
    @staticmethod
    @transaction.atomic
    def fail_refund_on_webhook(fedapay_payout: FedaPayPayout) -> None:
        """
        Called by webhook handler when payout fails.
        Marks refund request as failed.
        """
        refund_request_id = fedapay_payout.custom_metadata.get('refund_request_id')
        if not refund_request_id:
            logger.warning(f"No refund_request_id in FedaPay payout {fedapay_payout.id}")
            return
        
        try:
            refund_request = RefundRequest.objects.select_for_update().get(id=refund_request_id)
        except RefundRequest.DoesNotExist:
            logger.error(f"RefundRequest {refund_request_id} not found")
            return
        
        # Mark as failed (admin can retry)
        refund_request.status = 'pending'
        refund_request.admin_notes = (refund_request.admin_notes or '') + f"\n\nPayout failed: {fedapay_payout.last_error_code}"
        refund_request.save()
        
        # Log failure
        ParticipantActivityLog.objects.create(
            participant=refund_request.participant,
            activity_type="refund_failed",
            description=f"Refund payout failed: {fedapay_payout.last_error_code}",
        )
        
        logger.warning(f"RefundRequest {refund_request.id} payout failed: {fedapay_payout.last_error_code}")
    
    @staticmethod
    @transaction.atomic
    def process_refund_to_wallet(refund_request: RefundRequest, admin_participant) -> dict:
        """
        Alternative method: Process refund directly to participant's wallet (not through gateway).
        Used for internal wallet-to-wallet refunds.
        """
        # Lock the refund request
        refund_request = RefundRequest.objects.select_for_update().get(id=refund_request.id)
        
        # Validate current status
        if refund_request.status != 'pending':
            raise ValueError(f"Refund request is not pending. Current status: {refund_request.status}")
        
        # Validate patient role
        if refund_request.participant.role != 'patient':
            raise ValueError("Only patient refund requests can be processed")
        
        # Check for duplicate refunds
        if refund_request.transaction:
            existing_refunds = RefundRequest.objects.filter(
                transaction=refund_request.transaction,
                status__in=['completed', 'processing']
            ).exclude(id=refund_request.id)
            
            if existing_refunds.exists():
                raise ValueError("A refund for this transaction is already being processed or completed")
            
            # Validate refund amount excludes transaction fees
            max_refundable = refund_request.get_max_refundable_amount()
            if refund_request.amount > max_refundable:
                raise ValueError(f"Refund amount {refund_request.amount} exceeds maximum refundable amount {max_refundable} (transaction fees excluded)")
        
        # Check insurance claim conflicts
        if refund_request.insurance_claim:
            if refund_request.insurance_claim.status == 'paid':
                raise ValueError("Cannot refund - insurance claim already paid")
        
        # Get or create wallet
        wallet, _ = Wallet.objects.select_for_update().get_or_create(
            participant=refund_request.participant,
            defaults={'currency': refund_request.currency, 'balance': Decimal('0.00')}
        )
        
        # Create refund transaction
        # NOTE: Refund amount already excludes transaction fees (validated in get_max_refundable_amount)
        balance_before = wallet.balance
        balance_after = balance_before + refund_request.amount
        
        refund_txn = Transaction.objects.create(
            transaction_ref=f"REFUND-{refund_request.id}",
            wallet=wallet,
            transaction_type='refund',
            amount=refund_request.amount,
            currency=refund_request.currency,
            status='completed',
            payment_method='wallet',
            description=f"Refund to wallet: {refund_request.reason}",
            balance_before=balance_before,
            balance_after=balance_after,
            completed_at=timezone.now(),
            metadata={
                'refund_request_id': str(refund_request.id),
                'refund_type': refund_request.request_type,
                'approved_by': admin_participant.email
            }
        )
        
        # Update wallet balance
        wallet.balance = balance_after
        wallet.last_transaction_date = timezone.now()
        wallet.save()
        
        # Complete refund request
        refund_request.status = 'completed'
        refund_request.refund_transaction = refund_txn
        refund_request.admin_reviewer = admin_participant
        refund_request.reviewed_at = timezone.now()
        refund_request.processed_at = timezone.now()
        refund_request.save()
        
        # Log activity
        ParticipantActivityLog.objects.create(
            participant=refund_request.participant,
            activity_type="refund_completed",
            description=f"Refund of {refund_request.amount} {refund_request.currency} credited to wallet",
        )
        
        AuditLogEntry.objects.create(
            participant=admin_participant,
            action_type="update",
            resource_type="refund_request",
            resource_id=str(refund_request.id),
            details={
                "action": "approve_wallet_refund",
                "amount": float(refund_request.amount),
                "currency": refund_request.currency,
                "participant_email": refund_request.participant.email,
                "new_balance": float(wallet.balance)
            },
        )
        
        return {
            'success': True,
            'refund_request': refund_request,
            'refund_transaction': refund_txn,
            'new_wallet_balance': wallet.balance,
            'message': 'Refund credited to wallet successfully'
        }
