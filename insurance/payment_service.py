"""
Insurance Payment Service
Handles premium payments, recurring payments, and claim reimbursements
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from .models import InsuranceSubscription, InsurancePackage, InsuranceInvoice
from core.models import Participant, Wallet, Transaction as CoreTransaction
from payments.fedapay_webhook_handler import FedaPayWalletService
from currency_converter.services import CurrencyConverterService
from communication.notification_service import NotificationService

logger = logging.getLogger(__name__)


class InsurancePaymentService:
    """Service for handling insurance payments"""
    
    @staticmethod
    @transaction.atomic
    def generate_premium_invoice(subscription: InsuranceSubscription) -> InsuranceInvoice:
        """Generate invoice for insurance premium payment"""
        
        # Calculate next billing date based on frequency
        if subscription.next_billing_date:
            invoice_date = subscription.next_billing_date
        else:
            invoice_date = timezone.now().date()
        
        # Determine due date (7 days from invoice date)
        due_date = invoice_date + timedelta(days=7)
        
        # Create invoice
        invoice = InsuranceInvoice.objects.create(
            subscription=subscription,
            insurance_package=subscription.insurance_package,
            patient=subscription.patient,
            billing_period_start=invoice_date,
            billing_period_end=InsurancePaymentService._calculate_period_end(
                invoice_date, 
                subscription.payment_frequency
            ),
            amount=subscription.premium_amount,
            currency='USD',  # All amounts stored in USD
            due_date=due_date,
            status='pending',
            payment_method='pending',
            metadata={
                'subscription_id': str(subscription.id),
                'package_name': subscription.insurance_package.name,
                'payment_frequency': subscription.payment_frequency
            }
        )
        
        # Notify patient about new invoice
        patient_currency = CurrencyConverterService.get_participant_currency(subscription.patient)
        display_amount = CurrencyConverterService.convert(
            Decimal(str(invoice.amount)) / 100,
            'USD',  # Invoice amount is in USD
            patient_currency
        )
        NotificationService.create_notification(
            recipient=subscription.patient,
            notification_type='insurance',
            title='Nouvelle facture d\'assurance',
            message=f'Votre facture d\'assurance de {display_amount:.2f} {patient_currency} est disponible. Date limite: {due_date.strftime("%d/%m/%Y")}',
            action_url=f'/patient/insurance/invoices/',
            metadata={'invoice_id': str(invoice.id)}
        )
        
        logger.info(f"Invoice {invoice.id} generated for subscription {subscription.id}")
        return invoice
    
    @staticmethod
    def _calculate_period_end(start_date, frequency):
        """Calculate billing period end date"""
        if frequency == 'monthly':
            return start_date + relativedelta(months=1) - timedelta(days=1)
        elif frequency == 'quarterly':
            return start_date + relativedelta(months=3) - timedelta(days=1)
        elif frequency == 'semi_annual':
            return start_date + relativedelta(months=6) - timedelta(days=1)
        elif frequency == 'annual':
            return start_date + relativedelta(years=1) - timedelta(days=1)
        return start_date + relativedelta(months=1) - timedelta(days=1)
    
    @staticmethod
    @transaction.atomic
    def process_wallet_payment(invoice: InsuranceInvoice, patient: Participant) -> dict:
        """Process insurance premium payment from patient wallet"""
        
        try:
            # Get patient wallet
            wallet = Wallet.objects.select_for_update().get(participant=patient)
            
            # Check sufficient balance
            if wallet.balance < invoice.amount:
                return {
                    'success': False,
                    'error': 'Insufficient wallet balance',
                    'balance': wallet.balance,
                    'required': invoice.amount
                }
            
            # Create transaction record
            balance_before = wallet.balance
            balance_after = balance_before - invoice.amount
            
            core_txn = CoreTransaction.objects.create(
                transaction_ref=f"INS-PREMIUM-{invoice.id}",
                wallet=wallet,
                transaction_type='insurance_premium',
                amount=invoice.amount,
                currency=invoice.currency,
                status='completed',
                payment_method='wallet',
                description=f"Paiement prime d'assurance - {invoice.insurance_package.name}",
                balance_before=balance_before,
                balance_after=balance_after,
                completed_at=timezone.now(),
                metadata={
                    'invoice_id': str(invoice.id),
                    'subscription_id': str(invoice.subscription.id),
                    'package_name': invoice.insurance_package.name
                }
            )
            
            # Update wallet balance
            wallet.balance = balance_after
            wallet.last_transaction_date = timezone.now()
            wallet.save()
            
            # Update invoice
            invoice.status = 'paid'
            invoice.payment_method = 'wallet'
            invoice.paid_at = timezone.now()
            invoice.transaction_reference = core_txn.transaction_ref
            invoice.save()
            
            # Update subscription
            subscription = invoice.subscription
            subscription.last_payment_date = timezone.now().date()
            subscription.next_billing_date = InsurancePaymentService._calculate_next_billing_date(
                subscription.next_billing_date or timezone.now().date(),
                subscription.payment_frequency
            )
            subscription.save()
            
            # Notify patient
            patient_currency = CurrencyConverterService.get_participant_currency(patient)
            patient_amount = CurrencyConverterService.convert(
                Decimal(str(invoice.amount)) / 100,
                'USD',
                patient_currency
            )
            NotificationService.create_notification(
                recipient=patient,
                notification_type='payment',
                title='Paiement confirmé',
                message=f'Votre prime d\'assurance de {patient_amount:.2f} {patient_currency} a été payée avec succès',
                action_url=f'/patient/insurance/invoices/',
                metadata={'invoice_id': str(invoice.id), 'transaction_id': str(core_txn.id)}
            )
            
            # Notify insurance company
            company_currency = CurrencyConverterService.get_participant_currency(subscription.insurance_package.company)
            company_amount = CurrencyConverterService.convert(
                Decimal(str(invoice.amount)) / 100,
                'USD',
                company_currency
            )
            NotificationService.create_notification(
                recipient=subscription.insurance_package.company,
                notification_type='payment',
                title='Paiement de prime reçu',
                message=f'Paiement de {company_amount:.2f} {company_currency} reçu de {patient.full_name}',
                action_url=f'/insurance/invoices/',
                metadata={'invoice_id': str(invoice.id)}
            )
            
            logger.info(f"Wallet payment processed for invoice {invoice.id}")
            
            return {
                'success': True,
                'transaction_id': str(core_txn.id),
                'invoice_id': str(invoice.id),
                'amount': invoice.amount,
                'new_balance': balance_after
            }
            
        except Wallet.DoesNotExist:
            logger.error(f"Wallet not found for patient {patient.uid}")
            return {'success': False, 'error': 'Wallet not found'}
        except Exception as e:
            logger.error(f"Error processing wallet payment: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    @transaction.atomic
    def initiate_fedapay_payment(invoice: InsuranceInvoice, patient: Participant, callback_url: str) -> dict:
        """Initiate FedaPay payment for insurance premium"""
        
        try:
            result = FedaPayWalletService.initiate_wallet_topup(
                participant=patient,
                amount=invoice.amount,
                currency=invoice.currency,
                callback_url=callback_url
            )
            
            # Update invoice with payment reference
            invoice.transaction_reference = result['fedapay_transaction_id']
            invoice.payment_method = 'mobile_money'
            invoice.save()
            
            logger.info(f"FedaPay payment initiated for invoice {invoice.id}")
            
            return {
                'success': True,
                'payment_url': result['payment_url'],
                'payment_token': result['payment_token'],
                'transaction_id': result['transaction_id']
            }
            
        except Exception as e:
            logger.error(f"Error initiating FedaPay payment: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _calculate_next_billing_date(current_date, frequency):
        """Calculate next billing date based on frequency"""
        if frequency == 'monthly':
            return current_date + relativedelta(months=1)
        elif frequency == 'quarterly':
            return current_date + relativedelta(months=3)
        elif frequency == 'semi_annual':
            return current_date + relativedelta(months=6)
        elif frequency == 'annual':
            return current_date + relativedelta(years=1)
        return current_date + relativedelta(months=1)
    
    @staticmethod
    @transaction.atomic
    def process_claim_reimbursement(claim, approved_amount: Decimal) -> dict:
        """Process reimbursement for approved insurance claim"""
        from .models import InsuranceClaim
        
        try:
            # Get patient wallet
            wallet = Wallet.objects.select_for_update().get(participant=claim.patient)
            
            # Create transaction record
            balance_before = wallet.balance
            balance_after = balance_before + approved_amount
            
            core_txn = CoreTransaction.objects.create(
                transaction_ref=f"INS-REIMBURSE-{claim.claim_number}",
                wallet=wallet,
                transaction_type='insurance_reimbursement',
                amount=approved_amount,
                currency=CurrencyConverterService.get_participant_currency(claim.patient),
                status='completed',
                payment_method='wallet',
                description=f"Remboursement réclamation {claim.claim_number}",
                balance_before=balance_before,
                balance_after=balance_after,
                completed_at=timezone.now(),
                metadata={
                    'claim_id': str(claim.id),
                    'claim_number': claim.claim_number
                }
            )
            
            # Update wallet
            wallet.balance = balance_after
            wallet.last_transaction_date = timezone.now()
            wallet.save()
            
            # Update claim
            claim.status = 'paid'
            claim.paid_amount = approved_amount
            claim.payment_date = timezone.now()
            claim.save()
            
            # Notify patient
            patient_currency = CurrencyConverterService.get_participant_currency(claim.patient)
            display_amount = CurrencyConverterService.convert(
                Decimal(str(approved_amount)) / 100,
                'USD',
                patient_currency
            )
            NotificationService.create_notification(
                recipient=claim.patient,
                notification_type='insurance',
                title='Remboursement reçu',
                message=f'Remboursement de {display_amount:.2f} {patient_currency} pour la réclamation #{claim.claim_number}',
                action_url=f'/patient/insurance/claims/',
                metadata={'claim_id': str(claim.id), 'transaction_id': str(core_txn.id)}
            )
            
            logger.info(f"Claim reimbursement processed: {claim.claim_number}")
            
            return {
                'success': True,
                'transaction_id': str(core_txn.id),
                'amount': approved_amount,
                'new_balance': balance_after
            }
            
        except Wallet.DoesNotExist:
            logger.error(f"Wallet not found for patient {claim.patient.uid}")
            return {'success': False, 'error': 'Wallet not found'}
        except Exception as e:
            logger.error(f"Error processing reimbursement: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def check_overdue_invoices():
        """Check for overdue invoices and suspend subscriptions"""
        
        today = timezone.now().date()
        overdue_invoices = InsuranceInvoice.objects.filter(
            status='pending',
            due_date__lt=today
        ).select_related('subscription', 'patient')
        
        for invoice in overdue_invoices:
            invoice.status = 'overdue'
            invoice.save()
            
            # Check if subscription should be suspended (30 days overdue)
            days_overdue = (today - invoice.due_date).days
            
            if days_overdue > 30 and invoice.subscription.status == 'active':
                invoice.subscription.status = 'suspended'
                invoice.subscription.save()
                
                # Notify patient
                patient_currency = CurrencyConverterService.get_participant_currency(invoice.patient)
                display_amount = CurrencyConverterService.convert(
                    Decimal(str(invoice.amount)) / 100,
                    'USD',
                    patient_currency
                )
                NotificationService.create_notification(
                    recipient=invoice.patient,
                    notification_type='insurance',
                    title='Abonnement suspendu',
                    message=f'Votre abonnement d\'assurance a été suspendu pour non-paiement. Veuillez régler votre facture de {display_amount:.2f} {patient_currency}.',
                    action_url=f'/patient/insurance/invoices/',
                    metadata={'invoice_id': str(invoice.id)}
                )
                
                logger.warning(f"Subscription {invoice.subscription.id} suspended due to non-payment")
            
            elif days_overdue > 7:
                # Send reminder notification
                patient_currency = CurrencyConverterService.get_participant_currency(invoice.patient)
                display_amount = CurrencyConverterService.convert(
                    Decimal(str(invoice.amount)) / 100,
                    'USD',
                    patient_currency
                )
                NotificationService.create_notification(
                    recipient=invoice.patient,
                    notification_type='insurance',
                    title='Facture en retard',
                    message=f'Votre facture d\'assurance de {display_amount:.2f} {patient_currency} est en retard de {days_overdue} jours.',
                    action_url=f'/patient/insurance/invoices/',
                    metadata={'invoice_id': str(invoice.id)}
                )
