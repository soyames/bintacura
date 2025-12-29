"""
Pharmacy Payment Service
Integrates PharmacyOrders with existing payment infrastructure:
- QR code generation using qrcode_generator app
- Fedapay gateway integration for mobile money
- Payment receipts and transactions
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from qrcode_generator.services import QRCodeService
from payments.models import GatewayTransaction, ServiceTransaction, PaymentReceipt
from payments.fedapay_webhook_handler import FedaPayWalletService
from core.models import Participant

logger = logging.getLogger(__name__)


class PharmacyPaymentService:
    """Handle all payment operations for pharmacy orders"""

    @staticmethod
    def generate_order_qr_code(order):
        """
        Generate QR code for pharmacy order using existing QRCodeService.

        QR Data includes:
        - order_id: For resolving the order
        - order_number: Human-readable reference
        - patient_id: participant.uid of the patient
        - pharmacy_id: participant.uid of the pharmacy
        - total_amount: Order total
        - currency: Order currency
        - payment_status: Current payment status
        - payment_method: Selected payment method
        - verification_url: Backend endpoint to resolve payment
        """
        try:
            qr_data = {
                'type': 'pharmacy_order',
                'order_id': str(order.id),
                'order_number': order.order_number,
                'patient_id': str(order.patient.uid),
                'patient_name': order.patient.full_name,
                'pharmacy_id': str(order.pharmacy.uid),
                'pharmacy_name': order.pharmacy.full_name,
                'total_amount': str(order.total_amount / 100),  # Convert from minor units
                'currency': order.currency,
                'payment_status': order.payment_status,
                'payment_method': order.payment_method,
                'verification_url': f"{settings.FRONTEND_URL}/api/pharmacy/verify-order/{order.id}",
                'payment_url': f"{settings.FRONTEND_URL}/api/pharmacy/pay-order/{order.id}",
            }

            # Use existing QRCodeService to generate QR code
            qr_code_obj = QRCodeService.generate_qr_code(
                content_type='pharmacy_order',
                object_id=str(order.id),
                data_dict=qr_data
            )

            logger.info(f"QR code generated for pharmacy order {order.order_number}")
            return qr_code_obj

        except Exception as e:
            logger.error(f"Failed to generate QR code for order {order.order_number}: {e}")
            return None

    @staticmethod
    def verify_order_qr(qr_data):
        """
        Verify QR code data and return order information.
        Called when QR code is scanned.
        """
        try:
            import json
            from pharmacy.models import PharmacyOrder

            if isinstance(qr_data, str):
                data = json.loads(qr_data)
            else:
                data = qr_data

            if data.get('type') != 'pharmacy_order':
                return {'valid': False, 'error': 'Invalid QR code type'}

            order_id = data.get('order_id')
            if not order_id:
                return {'valid': False, 'error': 'Invalid QR code data'}

            order = PharmacyOrder.objects.select_related('patient', 'pharmacy').filter(id=order_id).first()

            if not order:
                return {'valid': False, 'error': 'Order not found'}

            return {
                'valid': True,
                'order': order,
                'order_number': order.order_number,
                'patient': {
                    'id': str(order.patient.uid),
                    'name': order.patient.full_name,
                    'phone': order.patient.phone_number or order.patient.phone,
                },
                'pharmacy': {
                    'id': str(order.pharmacy.uid),
                    'name': order.pharmacy.full_name,
                },
                'amount': order.total_amount / 100,
                'currency': order.currency,
                'payment_status': order.payment_status,
                'payment_method': order.payment_method,
            }

        except Exception as e:
            logger.error(f"Error verifying pharmacy order QR code: {e}")
            return {'valid': False, 'error': 'Verification failed'}

    @staticmethod
    @transaction.atomic
    def initiate_gateway_payment(order, callback_url=None):
        """
        Initiate payment through payment gateway (Fedapay) for card/mobile_money.
        Creates GatewayTransaction linked to order.
        """
        from pharmacy.models import PharmacyOrder
        from payments.fedapay_webhook_handler import FedaPayWalletService

        if order.payment_method not in ['card', 'mobile_money']:
            raise ValueError(f"Gateway payment not supported for payment method: {order.payment_method}")

        if order.payment_status == 'paid':
            raise ValueError("Order already paid")

        # Get patient phone number for mobile money
        patient_phone = order.patient.phone_number or order.patient.phone

        # Create gateway transaction
        gateway_txn = GatewayTransaction.objects.create(
            patient=order.patient,
            gateway_provider='fedapay',
            transaction_type='pharmacy_order',
            amount=Decimal(str(order.total_amount)) / 100,  # Convert to major units
            currency=order.currency,
            payment_method=order.payment_method,
            description=f"Pharmacy order {order.order_number}",
            reference_id=str(order.id),
            customer_phone=patient_phone,
            metadata={
                'order_id': str(order.id),
                'order_number': order.order_number,
                'pharmacy_id': str(order.pharmacy.uid),
                'patient_id': str(order.patient.uid),
            }
        )

        # Initiate Fedapay transaction
        try:
            callback = callback_url or f"{settings.FRONTEND_URL}/api/pharmacy/payment-callback/{order.id}"

            result = FedaPayWalletService.initiate_wallet_topup(
                participant=order.patient,
                amount=Decimal(str(order.total_amount)) / 100,
                currency=order.currency,
                callback_url=callback
            )

            # Update gateway transaction with Fedapay details
            gateway_txn.gateway_transaction_id = result['fedapay_transaction_id']
            gateway_txn.payment_url = result['payment_url']
            gateway_txn.save()

            # Update order with payment reference
            order.payment_reference = f"FEDAPAY-{result['fedapay_transaction_id']}"
            order.save()

            logger.info(f"Gateway payment initiated for order {order.order_number}")

            return {
                'success': True,
                'gateway_transaction_id': str(gateway_txn.id),
                'payment_url': result['payment_url'],
                'payment_token': result.get('payment_token'),
                'amount': order.total_amount / 100,
                'currency': order.currency,
            }

        except Exception as e:
            logger.error(f"Failed to initiate gateway payment for order {order.order_number}: {e}")
            gateway_txn.status = 'failed'
            gateway_txn.last_error_message = str(e)
            gateway_txn.save()
            raise

    @staticmethod
    @transaction.atomic
    def process_mobile_money_push(order, scanner_participant):
        """
        Provider (pharmacy staff) scans patient QR code and initiates mobile money push.

        Args:
            order: PharmacyOrder instance
            scanner_participant: Participant who scanned (must be pharmacy staff)

        Returns:
            dict with payment initiation details
        """
        from pharmacy.models import PharmacyOrder

        # Verify scanner is from the pharmacy
        if scanner_participant.uid != order.pharmacy.uid:
            # Check if scanner is pharmacy staff
            from pharmacy.models import PharmacyStaff
            is_staff = PharmacyStaff.objects.filter(
                pharmacy=order.pharmacy,
                staff_participant=scanner_participant,
                is_active=True
            ).exists()

            if not is_staff:
                raise PermissionError("Only pharmacy staff can initiate payment")

        if order.payment_status == 'paid':
            raise ValueError("Order already paid")

        if order.payment_method != 'mobile_money':
            raise ValueError(f"Mobile money push not supported for payment method: {order.payment_method}")

        # Get patient phone number
        patient_phone = order.patient.phone_number or order.patient.phone
        if not patient_phone:
            raise ValueError("Patient phone number not found")

        # Initiate gateway payment (will trigger mobile money push)
        result = PharmacyPaymentService.initiate_gateway_payment(
            order=order,
            callback_url=f"{settings.FRONTEND_URL}/api/pharmacy/payment-callback/{order.id}"
        )

        logger.info(f"Mobile money push initiated by {scanner_participant.full_name} for order {order.order_number}")

        return {
            **result,
            'message': f'Demande de paiement envoyée à {order.patient.full_name} ({patient_phone})',
            'patient_phone': patient_phone,
        }

    @staticmethod
    @transaction.atomic
    def create_payment_receipt(order):
        """
        Create payment receipt for completed pharmacy order.
        Integrates with existing PaymentReceipt model.
        """
        from pharmacy.models import PharmacyOrder

        if order.payment_status != 'paid':
            raise ValueError("Cannot create receipt for unpaid order")

        # Check if receipt already exists
        existing_receipt = PaymentReceipt.objects.filter(
            reference_id=str(order.id)
        ).first()

        if existing_receipt:
            return existing_receipt

        # Calculate amounts
        total_amount = Decimal(str(order.total_amount)) / 100  # Convert to major units

        # Create receipt
        receipt = PaymentReceipt.objects.create(
            receipt_number=f"PHARM-{order.order_number}",
            invoice_number=order.order_number,
            issued_to=order.patient,
            issued_by=order.pharmacy,
            service_type='pharmacy_order',
            service_description=f"Medication order from {order.pharmacy.full_name}",
            total_amount=total_amount,
            amount_paid=total_amount,
            currency=order.currency,
            payment_status='paid',
            payment_method=order.payment_method,
            payment_date=timezone.now(),
            reference_id=str(order.id),
            metadata={
                'order_number': order.order_number,
                'pharmacy_id': str(order.pharmacy.uid),
                'patient_id': str(order.patient.uid),
                'payment_reference': order.payment_reference,
            }
        )

        # Generate QR code for receipt using payments QR service
        from payments.qr_service import QRCodeService as PaymentQRService
        PaymentQRService.generate_invoice_qr_code(receipt)

        logger.info(f"Payment receipt {receipt.receipt_number} created for order {order.order_number}")

        return receipt
