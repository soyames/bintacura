import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from payments.models import (
    ParticipantGatewayAccount,
    FedaPayCustomer,
    GatewayTransaction,
    ServiceTransaction,
    TransactionFee
)
from payments.fedapay_service import fedapay_service

logger = logging.getLogger(__name__)


class FedaPayGatewayService:  # Service class for FedaPayGateway operations

    @staticmethod
    def get_or_create_fedapay_customer(participant, participant_phone):  # Get or create fedapay customer
        try:
            fedapay_customer = FedaPayCustomer.objects.filter(participant=participant).first()

            if fedapay_customer:
                return fedapay_customer

            customer_data = fedapay_service.create_customer(participant)
            customer_id = customer_data.get('v1', customer_data).get('id')

            fedapay_customer = FedaPayCustomer.objects.create(
                participant=participant,
                fedapay_customer_id=customer_id,
                email=participant.email,
                phone_number=participant_phone.phone_number if participant_phone else participant.phone_number
            )

            return fedapay_customer

        except Exception as e:
            logger.error(f"Failed to create FedaPay customer: {str(e)}")
            raise

    @staticmethod
    @transaction.atomic
    def create_payment_gateway_account(participant, participant_phone, gateway_provider, payout_mode=None):  # Create payment gateway account
        try:
            if gateway_provider == 'fedapay':
                fedapay_customer = FedaPayGatewayService.get_or_create_fedapay_customer(participant, participant_phone)
                gateway_customer_id = fedapay_customer.fedapay_customer_id
            else:
                gateway_customer_id = ''

            existing = ParticipantGatewayAccount.objects.filter(
                participant=participant,
                gateway_provider=gateway_provider,
                gateway_account_number=participant_phone.phone_number
            ).first()

            if existing:
                return existing

            gateway_account = ParticipantGatewayAccount.objects.create(
                participant=participant,
                participant_phone=participant_phone,
                gateway_provider=gateway_provider,
                gateway_customer_id=gateway_customer_id,
                gateway_account_number=participant_phone.phone_number,
                payout_mode=payout_mode or '',
                account_verified=True,
                is_active=True,
                is_default=not ParticipantGatewayAccount.objects.filter(participant=participant).exists()
            )

            return gateway_account

        except Exception as e:
            logger.error(f"Failed to create gateway account: {str(e)}")
            raise

    @staticmethod
    @transaction.atomic
    def initiate_payment_collection(service_transaction, patient_phone, provider_phone, callback_url):  # Initiate payment collection
        try:
            patient = service_transaction.patient
            service_provider = service_transaction.service_provider

            patient_fedapay = FedaPayGatewayService.get_or_create_fedapay_customer(patient, patient_phone)
            provider_fedapay = FedaPayGatewayService.get_or_create_fedapay_customer(service_provider, provider_phone)

            fee_details = service_transaction.fee_details
            net_amount_cents = int(fee_details.net_amount_to_provider * 100)

            transaction_data = fedapay_service.create_transaction(
                amount=service_transaction.amount,
                currency=service_transaction.currency,
                description=service_transaction.service_description,
                customer_id=int(patient_fedapay.fedapay_customer_id),
                callback_url=callback_url,
                custom_metadata={
                    'service_transaction_id': str(service_transaction.id),
                    'service_type': service_transaction.service_type,
                    'patient_email': patient.email,
                    'provider_email': service_provider.email,
                }
            )

            payment_token_data = fedapay_service.generate_payment_token(
                transaction_data['v1']['id']
            )

            gateway_txn = GatewayTransaction.objects.create(
                gateway_provider='fedapay',
                gateway_transaction_id=str(transaction_data['v1']['id']),
                gateway_reference=transaction_data['v1'].get('reference', ''),
                transaction_type='payment_collection',
                patient=patient,
                service_provider=service_provider,
                patient_phone=patient_phone,
                provider_phone=provider_phone,
                amount=service_transaction.amount,
                currency=service_transaction.currency,
                status='pending',
                payment_url=payment_token_data['v1']['url'],
                payment_token=payment_token_data['v1']['token'],
                metadata={
                    'service_transaction_id': str(service_transaction.id),
                    'provider_fedapay_customer_id': provider_fedapay.fedapay_customer_id,
                    'net_amount_to_provider': str(fee_details.net_amount_to_provider),
                }
            )

            service_transaction.gateway_transaction = gateway_txn
            service_transaction.status = 'processing'
            service_transaction.save()

            return {
                'success': True,
                'gateway_transaction_id': str(gateway_txn.id),
                'payment_url': payment_token_data['v1']['url'],
                'payment_token': payment_token_data['v1']['token'],
                'transaction_ref': service_transaction.transaction_ref,
            }

        except Exception as e:
            logger.error(f"Failed to initiate payment collection: {str(e)}")
            raise

    @staticmethod
    def get_transaction_status(gateway_transaction_id):  # Get transaction status
        try:
            gateway_txn = GatewayTransaction.objects.get(id=gateway_transaction_id)

            if not gateway_txn.gateway_transaction_id:
                return {
                    'status': gateway_txn.status,
                    'message': 'No external transaction ID'
                }

            fedapay_data = fedapay_service.get_transaction(int(gateway_txn.gateway_transaction_id))

            return {
                'status': fedapay_data['v1']['status'],
                'reference': fedapay_data['v1'].get('reference'),
                'amount': fedapay_data['v1']['amount'] / 100,
                'fees': fedapay_data['v1'].get('fees', 0) / 100,
                'approved_at': fedapay_data['v1'].get('approved_at'),
            }

        except GatewayTransaction.DoesNotExist:
            return {
                'error': 'Transaction not found'
            }
        except Exception as e:
            logger.error(f"Failed to get transaction status: {str(e)}")
            return {
                'error': str(e)
            }
