import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from core.models import Participant
from payments.models import (
    ServiceCatalog,
    ServiceTransaction,
    TransactionFee,
    ParticipantPhone,
    PaymentReceipt
)
from payments.fee_service import FeeCalculationService
from payments.services.fedapay_gateway_service import FedaPayGatewayService

logger = logging.getLogger(__name__)


class ServiceTransactionService:  # Service class for Transaction operations

    @staticmethod
    def calculate_transaction_fees(amount):  # Calculate transaction fees
        return FeeCalculationService.calculate_service_payment_fees(amount)

    @staticmethod
    @transaction.atomic
    def create_service_transaction(
        patient,
        service_provider,
        service_catalog_item,
        service_type,
        service_id,
        service_description,
        amount,
        currency,
        payment_method,
        patient_phone=None,
        provider_phone=None
    ):
        try:
            fee_calculation = ServiceTransactionService.calculate_transaction_fees(amount)

            service_txn = ServiceTransaction.objects.create(
                patient=patient,
                service_provider=service_provider,
                service_catalog_item=service_catalog_item,
                service_type=service_type,
                service_id=service_id,
                service_description=service_description,
                amount=amount,
                currency=currency,
                payment_method=payment_method,
                patient_phone=patient_phone,
                provider_phone=provider_phone,
                status='pending',
                metadata={
                    'created_from': 'api',
                    'service_catalog_name': service_catalog_item.service_name if service_catalog_item else None,
                }
            )

            TransactionFee.objects.create(
                service_transaction=service_txn,
                gross_amount=fee_calculation['gross_amount'],
                platform_fee_rate=Decimal('0.01'),
                platform_fee_amount=fee_calculation['platform_fee'],
                tax_rate=Decimal('0.18'),
                tax_amount=fee_calculation['tax'],
                total_fee_amount=fee_calculation['total_fee'],
                net_amount_to_provider=fee_calculation['net_amount'],
                metadata={
                    'fee_breakdown': fee_calculation['fee_breakdown']
                }
            )

            return service_txn

        except Exception as e:
            logger.error(f"Failed to create service transaction: {str(e)}")
            raise

    @staticmethod
    @transaction.atomic
    def process_onsite_payment(
        patient,
        service_provider,
        service_catalog_item,
        service_type,
        service_id,
        service_description,
        amount,
        currency
    ):
        try:
            service_txn = ServiceTransactionService.create_service_transaction(
                patient=patient,
                service_provider=service_provider,
                service_catalog_item=service_catalog_item,
                service_type=service_type,
                service_id=service_id,
                service_description=service_description,
                amount=amount,
                currency=currency,
                payment_method='onsite_cash'
            )

            service_txn.status = 'pending'
            service_txn.save()

            from payments.enhanced_receipt_service import EnhancedReceiptService
            
            receipt = EnhancedReceiptService.create_receipt_from_service_transaction(service_txn)

            return {
                'success': True,
                'service_transaction': service_txn,
                'service_transaction_id': str(service_txn.id),
                'transaction_ref': service_txn.transaction_ref,
                'receipt': receipt,
                'receipt_id': str(receipt.id),
                'receipt_url': f'/api/v1/payments/receipts/{receipt.id}/',
                'message': 'On-site payment recorded. Awaiting provider confirmation.',
                'fee_note': 'Platform fees will be deducted during payout'
            }

        except Exception as e:
            logger.error(f"Failed to process on-site payment: {str(e)}")
            raise

    @staticmethod
    @transaction.atomic
    def initiate_gateway_payment(
        patient,
        service_provider,
        service_catalog_item,
        service_type,
        service_id,
        service_description,
        amount,
        currency,
        payment_method,
        patient_phone_id,
        callback_url
    ):
        try:
            patient_phone = None
            if patient_phone_id:
                patient_phone = ParticipantPhone.objects.get(id=patient_phone_id, participant=patient)

                if not patient_phone.is_verified:
                    raise ValueError("Patient phone number must be verified before payment")

            provider_phone = ParticipantPhone.objects.filter(
                participant=service_provider,
                is_verified=True
            ).first()

            if not provider_phone:
                raise ValueError("Service provider must have a verified phone number")

            service_txn = ServiceTransactionService.create_service_transaction(
                patient=patient,
                service_provider=service_provider,
                service_catalog_item=service_catalog_item,
                service_type=service_type,
                service_id=service_id,
                service_description=service_description,
                amount=amount,
                currency=currency,
                payment_method=payment_method,
                patient_phone=patient_phone,
                provider_phone=provider_phone
            )

            if payment_method in ['fedapay_mobile', 'fedapay_card']:
                payment_result = FedaPayGatewayService.initiate_payment_collection(
                    service_transaction=service_txn,
                    patient_phone=patient_phone,
                    provider_phone=provider_phone,
                    callback_url=callback_url
                )

                return {
                    'success': True,
                    'service_transaction_id': str(service_txn.id),
                    'transaction_ref': service_txn.transaction_ref,
                    'payment_url': payment_result['payment_url'],
                    'payment_token': payment_result['payment_token'],
                    'amount': str(amount),
                    'currency': currency,
                    'fee_details': {
                        'gross_amount': str(service_txn.fee_details.gross_amount),
                        'platform_fee': str(service_txn.fee_details.platform_fee_amount),
                        'tax': str(service_txn.fee_details.tax_amount),
                        'total_fee': str(service_txn.fee_details.total_fee_amount),
                        'net_to_provider': str(service_txn.fee_details.net_amount_to_provider),
                    }
                }
            else:
                raise ValueError(f"Unsupported payment method: {payment_method}")

        except Exception as e:
            logger.error(f"Failed to initiate gateway payment: {str(e)}")
            raise

    @staticmethod
    def get_participant_transactions(participant, status=None):  # Get participant transactions
        queryset = ServiceTransaction.objects.filter(
            patient=participant
        ) | ServiceTransaction.objects.filter(
            service_provider=participant
        )

        if status:
            queryset = queryset.filter(status=status)

        return queryset.select_related(
            'patient',
            'service_provider',
            'service_catalog_item',
            'gateway_transaction',
            'fee_details'
        ).order_by('-created_at')
