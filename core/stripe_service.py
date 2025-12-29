import stripe
from django.conf import settings
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    @classmethod
    def create_customer(cls, email: str, name: str, metadata: Dict = None) -> Optional[str]:
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer for {email}: {str(e)}")
            return None

    @classmethod
    def create_payment_intent(cls, amount: int, currency: str, customer_id: str = None, metadata: Dict = None) -> Optional[Dict]:
        try:
            intent_data = {
                'amount': amount,
                'currency': currency.lower(),
                'metadata': metadata or {}
            }
            if customer_id:
                intent_data['customer'] = customer_id

            payment_intent = stripe.PaymentIntent.create(**intent_data)
            return {
                'id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'status': payment_intent.status,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create payment intent: {str(e)}")
            return None

    @classmethod
    def confirm_payment_intent(cls, payment_intent_id: str) -> bool:
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if payment_intent.status == 'requires_confirmation':
                payment_intent.confirm()
            return payment_intent.status == 'succeeded'
        except stripe.error.StripeError as e:
            logger.error(f"Failed to confirm payment intent {payment_intent_id}: {str(e)}")
            return False

    @classmethod
    def create_refund(cls, payment_intent_id: str, amount: int = None) -> Optional[Dict]:
        try:
            refund_data = {'payment_intent': payment_intent_id}
            if amount:
                refund_data['amount'] = amount

            refund = stripe.Refund.create(**refund_data)
            return {
                'id': refund.id,
                'status': refund.status,
                'amount': refund.amount,
                'currency': refund.currency
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create refund for {payment_intent_id}: {str(e)}")
            return None

    @classmethod
    def attach_payment_method(cls, payment_method_id: str, customer_id: str) -> bool:
        try:
            stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
            stripe.Customer.modify(
                customer_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Failed to attach payment method {payment_method_id} to customer {customer_id}: {str(e)}")
            return False

    @classmethod
    def create_payout(cls, amount: int, currency: str, destination: str = 'bank_account') -> Optional[Dict]:
        try:
            payout = stripe.Payout.create(
                amount=amount,
                currency=currency.lower(),
                destination=destination
            )
            return {
                'id': payout.id,
                'status': payout.status,
                'amount': payout.amount,
                'currency': payout.currency,
                'arrival_date': payout.arrival_date
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create payout: {str(e)}")
            return None

    @classmethod
    def get_payment_intent(cls, payment_intent_id: str) -> Optional[Dict]:
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'id': payment_intent.id,
                'status': payment_intent.status,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'customer': payment_intent.customer
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve payment intent {payment_intent_id}: {str(e)}")
            return None

    @classmethod
    def list_customer_payment_methods(cls, customer_id: str, type: str = 'card') -> list:
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type=type
            )
            return [
                {
                    'id': pm.id,
                    'type': pm.type,
                    'card': pm.card if pm.type == 'card' else None
                }
                for pm in payment_methods.data
            ]
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list payment methods for customer {customer_id}: {str(e)}")
            return []
