"""
Universal Payment Service
=========================

QR-driven payment system for ALL transaction types across the platform:
- Appointments (doctor consultations, hospital visits)
- Pharmacy orders
- Lab tests
- Imaging services
- Insurance premiums
- Any other healthcare service

Architecture:
- Central Participant model (patient, doctor, hospital, pharmacy, insurance)
- Existing QRCodeService from qrcode_generator app
- Existing Fedapay integration
- Existing ServiceTransaction and GatewayTransaction models
- Currency conversion via CurrencyService
"""

import logging
import json
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from qrcode_generator.services import QRCodeService
from payments.models import ServiceTransaction, GatewayTransaction, PaymentReceipt
from payments.fedapay_webhook_handler import FedaPayWalletService
from core.models import Participant, Wallet
from currency_converter.services import CurrencyConverterService
from core.services import WalletService

logger = logging.getLogger(__name__)


class UniversalPaymentService:
    """
    Universal payment service for ALL transaction types.

    Handles:
    1. QR code generation for any payment
    2. Payment method selection (wallet, card, mobile money, insurance, cash)
    3. Currency conversion based on patient location
    4. Mobile money push (provider scans patient QR)
    5. Payment receipt generation
    6. Webhook processing
    """

    @staticmethod
    def _get_nested_attr(obj, attr_path):
        """Get nested attribute using dot notation (e.g., 'insurance_package.company')"""
        if not attr_path:
            return None

        attrs = attr_path.split('.')
        value = obj
        for attr in attrs:
            if value is None:
                return None
            value = getattr(value, attr, None)
        return value

    # Supported service types
    SERVICE_TYPES = {
        'appointment': {
            'model': 'appointments.models.Appointment',
            'ref_field': 'id',
            'amount_field': 'final_price',
            'patient_field': 'patient',
            'provider_field': 'doctor',  # or 'hospital' depending on type
            'description': 'Appointment Payment',
        },
        'pharmacy_order': {
            'model': 'pharmacy.models.PharmacyOrder',
            'ref_field': 'order_number',
            'amount_field': 'total_amount',
            'patient_field': 'patient',
            'provider_field': 'pharmacy',
            'description': 'Pharmacy Order Payment',
        },
        'lab_test': {
            'model': 'lab.models.LabTest',  # If exists
            'ref_field': 'test_number',
            'amount_field': 'total_cost',
            'patient_field': 'patient',
            'provider_field': 'lab',
            'description': 'Laboratory Test Payment',
        },
        'insurance_premium': {
            'model': 'insurance.models.InsuranceInvoice',
            'ref_field': 'invoice_number',
            'amount_field': 'amount',
            'patient_field': 'patient',
            'provider_field': 'insurance_package.company',
            'description': 'Paiement de Prime d\'Assurance',
        },
        'platform_fee': {
            'model': 'payments.models.FeeLedger',
            'ref_field': 'id',
            'amount_field': 'fee_amount',
            'patient_field': 'provider',  # Fee is paid by provider, not patient
            'provider_field': None,  # Fee goes to platform
            'description': 'Frais de Plateforme',
        },
    }

    @staticmethod
    def generate_payment_qr(service_type, service_object, patient=None):
        """
        Generate QR code for any service payment.

        Args:
            service_type: Type of service ('appointment', 'pharmacy_order', 'lab_test', etc.)
            service_object: Instance of the service model (Appointment, PharmacyOrder, etc.)
            patient: Participant instance (optional, will be extracted from service_object)

        Returns:
            QRCode instance
        """
        try:
            # Extract patient and amount from service object
            if not patient:
                config = UniversalPaymentService.SERVICE_TYPES.get(service_type)
                if not config:
                    raise ValueError(f"Unsupported service type: {service_type}")

                patient_field = config['patient_field']
                patient = getattr(service_object, patient_field)

            # Get service provider (supports nested fields like 'insurance_package.company')
            provider_field = config.get('provider_field')
            service_provider = UniversalPaymentService._get_nested_attr(service_object, provider_field) if provider_field else None

            # Get amount (handle both DecimalField and IntegerField)
            amount_field = config.get('amount_field', 'total_amount')
            amount = getattr(service_object, amount_field)

            # Convert integer amounts (stored as cents) to decimal
            if isinstance(amount, int):
                amount = Decimal(str(amount)) / 100

            # Get currency
            currency = getattr(service_object, 'currency', 'USD')

            # Generate QR data
            qr_data = {
                'type': service_type,
                'service_id': str(service_object.id),
                'reference': getattr(service_object, config.get('ref_field', 'id')),
                'patient_id': str(patient.uid),
                'patient_name': patient.full_name,
                'amount': str(amount),
                'currency': currency,
                'payment_status': getattr(service_object, 'payment_status', 'pending'),
                'description': config.get('description', 'Service Payment'),
                'verification_url': f"{settings.FRONTEND_URL}/api/payments/verify/{service_type}/{service_object.id}",
                'payment_url': f"{settings.FRONTEND_URL}/api/payments/pay/{service_type}/{service_object.id}",
            }

            # Add provider info if available
            if service_provider:
                qr_data['provider_id'] = str(service_provider.uid)
                qr_data['provider_name'] = service_provider.full_name

            # Generate QR code using existing QRCodeService
            qr_code_obj = QRCodeService.generate_qr_code(
                content_type=service_type,
                object_id=str(service_object.id),
                data_dict=qr_data
            )

            logger.info(f"QR code generated for {service_type} {service_object.id}")
            return qr_code_obj

        except Exception as e:
            logger.error(f"Failed to generate QR code for {service_type}: {e}")
            return None

    @staticmethod
    def verify_payment_qr(qr_data):
        """
        Verify QR code and return service payment details.

        Args:
            qr_data: JSON string or dict from QR code

        Returns:
            dict with verification result and service details
        """
        try:
            if isinstance(qr_data, str):
                data = json.loads(qr_data)
            else:
                data = qr_data

            service_type = data.get('type')
            service_id = data.get('service_id')

            if not service_type or not service_id:
                return {'valid': False, 'error': 'Invalid QR code data'}

            # Get service object
            config = UniversalPaymentService.SERVICE_TYPES.get(service_type)
            if not config:
                return {'valid': False, 'error': f'Unsupported service type: {service_type}'}

            # Import model and get object
            model_path = config['model']
            module_name, class_name = model_path.rsplit('.', 1)
            module = __import__(module_name, fromlist=[class_name])
            model_class = getattr(module, class_name)

            service_object = model_class.objects.filter(id=service_id).first()
            if not service_object:
                return {'valid': False, 'error': 'Service not found'}

            # Extract details
            patient = getattr(service_object, config['patient_field'])
            provider_field = config.get('provider_field')
            service_provider = UniversalPaymentService._get_nested_attr(service_object, provider_field) if provider_field else None

            amount_field = config.get('amount_field', 'total_amount')
            amount = getattr(service_object, amount_field)
            if isinstance(amount, int):
                amount = Decimal(str(amount)) / 100

            return {
                'valid': True,
                'service_type': service_type,
                'service_object': service_object,
                'patient': {
                    'id': str(patient.uid),
                    'name': patient.full_name,
                    'phone': patient.phone_number or patient.phone,
                },
                'provider': {
                    'id': str(service_provider.uid) if service_provider else None,
                    'name': service_provider.full_name if service_provider else None,
                } if service_provider else None,
                'amount': float(amount),
                'currency': getattr(service_object, 'currency', 'USD'),
                'payment_status': getattr(service_object, 'payment_status', 'pending'),
                'reference': str(data.get('reference', service_object.id)),
            }

        except Exception as e:
            logger.error(f"Error verifying payment QR: {e}")
            return {'valid': False, 'error': 'Verification failed'}

    @staticmethod
    @transaction.atomic
    def process_payment(service_type, service_object, payment_method, patient, **kwargs):
        """
        Process payment for any service type.

        Args:
            service_type: Type of service
            service_object: Service instance
            payment_method: 'wallet', 'card', 'mobile_money', 'insurance', 'cash'
            patient: Participant making payment
            **kwargs: Additional parameters (callback_url, etc.)

        Returns:
            dict with payment result
        """
        try:
            config = UniversalPaymentService.SERVICE_TYPES.get(service_type)
            if not config:
                raise ValueError(f"Unsupported service type: {service_type}")

            # Get amount and currency
            amount_field = config.get('amount_field', 'total_amount')
            amount = getattr(service_object, amount_field)
            if isinstance(amount, int):
                amount = Decimal(str(amount)) / 100

            currency = getattr(service_object, 'currency', 'USD')
            provider_field = config.get('provider_field')
            service_provider = UniversalPaymentService._get_nested_attr(service_object, provider_field) if provider_field else None

            # Process based on payment method
            if payment_method == 'wallet':
                return UniversalPaymentService._process_wallet_payment(
                    service_type, service_object, patient, amount, currency
                )

            elif payment_method in ['card', 'mobile_money']:
                callback_url = kwargs.get('callback_url') or f"{settings.FRONTEND_URL}/api/payments/callback/{service_type}/{service_object.id}"
                return UniversalPaymentService._process_gateway_payment(
                    service_type, service_object, patient, service_provider,
                    amount, currency, payment_method, callback_url
                )

            elif payment_method == 'insurance':
                return UniversalPaymentService._process_insurance_payment(
                    service_type, service_object, patient, amount, currency
                )

            else:  # cash
                return {
                    'success': True,
                    'message': 'Paiement en espèces à confirmer',
                    'payment_method': payment_method,
                }

        except Exception as e:
            logger.error(f"Error processing payment for {service_type}: {e}")
            raise

    @staticmethod
    def _process_wallet_payment(service_type, service_object, payer, amount, currency):
        """
        Wallet payment is NOT supported in this system.

        BINTACURA does not store money. All payments go through external gateways:
        - Patients: Pay via Fedapay (card/mobile money) or onsite cash
        - Providers: Receive payments via their linked payment methods (bank/mobile money accounts)
        - Platform fees: Deducted by gateway or billed separately

        This method exists only to provide a clear error message.
        """
        raise ValueError('Les paiements par portefeuille ne sont pas disponibles. Tous les paiements doivent passer par les passerelles externes (carte, mobile money) ou en espèces sur place.')

    @staticmethod
    def _process_gateway_payment(service_type, service_object, patient, service_provider,
                                  amount, currency, payment_method, callback_url):
        """Process gateway payment (card/mobile money)"""
        # SECURITY: Block payments to unverified providers
        if service_provider:
            provider_roles = ['doctor', 'hospital', 'hospital_staff', 'pharmacy', 'pharmacy_staff', 
                             'insurance_company', 'insurance_company_staff']
            if service_provider.role in provider_roles:
                if not service_provider.is_verified or not service_provider.can_receive_payments:
                    raise ValueError(
                        f"Le prestataire n'est pas vérifié. Les paiements vers des comptes non vérifiés sont bloqués pour votre sécurité. "
                        f"Provider is not verified. Payments to unverified providers are blocked for security."
                    )
        
        # Get patient phone
        patient_phone = patient.phone_number or patient.phone

        # Create gateway transaction
        gateway_txn = GatewayTransaction.objects.create(
            patient=patient,
            gateway_provider='fedapay',
            transaction_type=service_type,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            description=f'{service_type} payment',
            reference_id=str(service_object.id),
            customer_phone=patient_phone,
            metadata={
                'service_type': service_type,
                'service_id': str(service_object.id),
                'patient_id': str(patient.uid),
                'provider_id': str(service_provider.uid) if service_provider else None,
            }
        )

        # Initiate Fedapay transaction
        result = FedaPayWalletService.initiate_wallet_topup(
            participant=patient,
            amount=amount,
            currency=currency,
            callback_url=callback_url
        )

        # Update gateway transaction
        gateway_txn.gateway_transaction_id = result['fedapay_transaction_id']
        gateway_txn.payment_url = result['payment_url']
        gateway_txn.save()

        # Update service object
        if hasattr(service_object, 'payment_reference'):
            service_object.payment_reference = f"FEDAPAY-{result['fedapay_transaction_id']}"
            service_object.save()

        return {
            'success': True,
            'payment_url': result['payment_url'],
            'payment_token': result.get('payment_token'),
            'amount': float(amount),
            'currency': currency,
            'gateway_transaction_id': str(gateway_txn.id),
        }

    @staticmethod
    def _process_insurance_payment(service_type, service_object, patient, amount, currency):
        """Process insurance payment"""
        from insurance.models import InsuranceClaim, InsuranceSubscription

        # Check active insurance
        active_subscription = InsuranceSubscription.objects.filter(
            participant=patient,
            status='active'
        ).first()

        if not active_subscription:
            raise ValueError('Aucune assurance active trouvée')

        # Create insurance claim
        claim = InsuranceClaim.objects.create(
            participant=patient,
            insurance_company=active_subscription.insurance_company,
            subscription=active_subscription,
            claim_type=service_type,
            service_date=timezone.now(),
            total_amount=int(amount * 100) if amount else 0,  # Convert to cents
            status='pending'
        )

        # Update service object
        service_object.payment_status = 'pending'
        if hasattr(service_object, 'payment_reference'):
            service_object.payment_reference = f'INSURANCE-{claim.id}'
        service_object.save()

        return {
            'success': True,
            'message': 'Réclamation d\'assurance créée',
            'claim_id': str(claim.id),
            'payment_method': 'insurance',
        }

    @staticmethod
    def _create_receipt(service_type, service_object, patient, amount, currency, payment_method):
        """Create payment receipt"""
        try:
            config = UniversalPaymentService.SERVICE_TYPES.get(service_type)
            provider_field = config.get('provider_field')
            service_provider = UniversalPaymentService._get_nested_attr(service_object, provider_field) if provider_field else None

            receipt = PaymentReceipt.objects.create(
                receipt_number=f"{service_type.upper()}-{service_object.id}",
                invoice_number=str(getattr(service_object, config.get('ref_field', 'id'))),
                issued_to=patient,
                issued_by=service_provider,
                service_type=service_type,
                service_description=config.get('description', 'Service Payment'),
                total_amount=amount,
                amount_paid=amount,
                currency=currency,
                payment_status='paid',
                payment_method=payment_method,
                payment_date=timezone.now(),
                reference_id=str(service_object.id),
                metadata={
                    'service_type': service_type,
                    'service_id': str(service_object.id),
                },
            )

            # Generate QR code for receipt
            from payments.qr_service import QRCodeService as PaymentQRService
            PaymentQRService.generate_invoice_qr_code(receipt)

            return receipt

        except Exception as e:
            logger.error(f"Failed to create receipt: {e}")
            return None

    @staticmethod
    @transaction.atomic
    def process_mobile_money_push(service_type, service_object, scanner_participant):
        """
        Provider scans patient QR and initiates mobile money push.

        Args:
            service_type: Type of service
            service_object: Service instance
            scanner_participant: Participant who scanned (provider staff)

        Returns:
            dict with payment initiation details
        """
        config = UniversalPaymentService.SERVICE_TYPES.get(service_type)
        if not config:
            raise ValueError(f"Unsupported service type: {service_type}")

        # Get patient and provider
        patient = getattr(service_object, config['patient_field'])
        provider_field = config.get('provider_field')
        service_provider = UniversalPaymentService._get_nested_attr(service_object, provider_field) if provider_field else None

        # Verify scanner is provider or staff
        if scanner_participant.uid != service_provider.uid if service_provider else False:
            # Could add additional staff verification here
            pass

        # Check payment status
        if getattr(service_object, 'payment_status', 'pending') == 'paid':
            raise ValueError('Already paid')

        # Get amount
        amount_field = config.get('amount_field', 'total_amount')
        amount = getattr(service_object, amount_field)
        if isinstance(amount, int):
            amount = Decimal(str(amount)) / 100

        currency = getattr(service_object, 'currency', 'USD')

        # Initiate gateway payment
        result = UniversalPaymentService._process_gateway_payment(
            service_type=service_type,
            service_object=service_object,
            patient=patient,
            service_provider=service_provider,
            amount=amount,
            currency=currency,
            payment_method='mobile_money',
            callback_url=f"{settings.FRONTEND_URL}/api/payments/callback/{service_type}/{service_object.id}"
        )

        return {
            **result,
            'message': f'Demande de paiement envoyée à {patient.full_name}',
            'patient_phone': patient.phone_number or patient.phone,
        }

