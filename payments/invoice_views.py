from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.db import models as db_models
from django.utils import timezone
from decimal import Decimal
from .models import PaymentReceipt, ServiceTransaction
from .enhanced_receipt_service import EnhancedReceiptService
from core.models import Participant
from currency_converter.services import CurrencyConverterService


class InvoiceListView(LoginRequiredMixin, TemplateView):
    """View for listing all invoices/receipts for a participant"""
    template_name = "payments/invoice_list.html"
    login_url = "/auth/login/"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        participant = self.request.user
        
        portal = self.request.path.split("/")[1]
        context["portal"] = portal
        
        # Get all invoice types
        all_invoices = []
        
        try:
            # 1. Payment Receipts (service payments)
            if participant.role == 'patient':
                receipts_qs = PaymentReceipt.objects.filter(
                    issued_to=participant
                )
                service_txns_qs = ServiceTransaction.objects.filter(
                    patient=participant
                )
            else:
                receipts_qs = PaymentReceipt.objects.filter(
                    db_models.Q(issued_to=participant) | db_models.Q(issued_by=participant)
                )
                service_txns_qs = ServiceTransaction.objects.filter(
                    service_provider=participant
                )
                
            receipts = receipts_qs.select_related(
                'issued_to', 'issued_by', 'service_transaction'
            ).order_by('-issued_at')
            
            # 2. Insurance Invoices (premiums)
            if participant.role == 'patient':
                try:
                    from insurance.models import InsuranceInvoice
                    insurance_invoices = InsuranceInvoice.objects.filter(
                        patient=participant
                    ).select_related('subscription', 'insurance_package').order_by('-issue_date')

                    # Add insurance invoices to the list
                    for inv in insurance_invoices:
                        all_invoices.append({
                            'id': inv.id,
                            'invoice_number': getattr(inv, 'invoice_number', str(inv.id)[:8]),
                            'type': 'insurance_premium',
                            'description': f'Prime d\'assurance - {inv.insurance_package.name}',
                            'amount': inv.amount,
                            'currency': 'XOF',
                            'status': inv.status.upper(),
                            'date': inv.issue_date,
                            'due_date': inv.due_date,
                            'paid_date': inv.paid_date,
                            'payment_method': inv.payment_method,
                            'period_start': inv.period_start,
                            'period_end': inv.period_end,
                        })
                except Exception as ins_err:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error loading insurance invoices: {str(ins_err)}")

            # 3. Hospital Bills
            if participant.role == 'patient':
                try:
                    from hospital.models import HospitalBill
                    hospital_bills = HospitalBill.objects.filter(
                        patient=participant
                    ).select_related('hospital', 'admission').order_by('-billing_date')

                    # Add hospital bills to the list
                    for bill in hospital_bills:
                        all_invoices.append({
                            'id': bill.id,
                            'invoice_number': bill.bill_number,
                            'type': 'hospital_bill',
                            'description': f'Facture hôpital - {bill.hospital.full_name}',
                            'amount': bill.balance_due or bill.total_amount,
                            'currency': 'XOF',
                            'status': bill.status.upper(),
                            'date': bill.billing_date,
                            'due_date': bill.due_date,
                            'paid_date': None if bill.status != 'paid' else bill.billing_date,
                            'payment_method': None,
                        })
                except Exception as hosp_err:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error loading hospital bills: {str(hosp_err)}")
            
            # Add payment receipts to the list
            for receipt in receipts:
                # Get description from service_details or service_transaction
                description = 'Paiement de service'
                if receipt.service_details:
                    description = str(receipt.service_details)
                elif hasattr(receipt, 'service_transaction') and receipt.service_transaction:
                    description = f'{receipt.service_transaction.service_type or "Service"}'

                all_invoices.append({
                    'id': receipt.id,
                    'invoice_number': receipt.receipt_number,
                    'type': 'service_payment',
                    'description': description,
                    'amount': receipt.total_amount,
                    'currency': receipt.currency or 'XOF',
                    'status': receipt.payment_status,
                    'date': receipt.issued_at.date() if receipt.issued_at else None,
                    'due_date': None,
                    'paid_date': receipt.payment_date.date() if receipt.payment_date else None,
                    'payment_method': receipt.payment_method,
                    'receipt_obj': receipt,
                })
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error filtering invoices for participant {participant.uid}: {str(e)}")
        
        # Sort all invoices by date
        all_invoices.sort(key=lambda x: x['date'] or timezone.now().date(), reverse=True)
        
        # Calculate statistics
        paid_count = sum(1 for inv in all_invoices if inv['status'] in ['PAID', 'paid'])
        unpaid_count = sum(1 for inv in all_invoices if inv['status'] in ['PENDING', 'pending'])
        overdue_count = sum(1 for inv in all_invoices if inv['status'] in ['overdue'])
        cancelled_count = sum(1 for inv in all_invoices if inv['status'] in ['FAILED', 'CANCELLED', 'cancelled'])
        refunded_count = sum(1 for inv in all_invoices if inv['status'] in ['REFUNDED', 'refunded'])
        
        from currency_converter.services import CurrencyConverterService

        # Get participant's currency using phone number and geolocation
        participant_currency = CurrencyConverterService.get_participant_currency(participant)

        # Calculate unpaid total with currency conversion
        unpaid_total = Decimal('0')
        for invoice in all_invoices:
            if invoice['status'] in ['PENDING', 'pending', 'overdue']:
                invoice_currency = invoice['currency'] or 'XOF'
                invoice_amount = invoice['amount'] or Decimal('0')
                if invoice_currency != participant_currency:
                    converted_amount = CurrencyConverterService.convert_amount(
                        invoice_amount,
                        invoice_currency,
                        participant_currency
                    )
                    unpaid_total += converted_amount
                else:
                    unpaid_total += invoice_amount

        # Convert invoice amounts to participant currency for display
        for invoice in all_invoices:
            invoice_currency = invoice['currency'] or 'XOF'
            if invoice_currency != participant_currency:
                invoice['converted_total_amount'] = CurrencyConverterService.convert_amount(
                    invoice['amount'] or Decimal('0'),
                    invoice_currency,
                    participant_currency
                )
                invoice['display_amount'] = invoice['converted_total_amount']
            else:
                invoice['converted_total_amount'] = invoice['amount']
                invoice['display_amount'] = invoice['amount']
            invoice['display_currency'] = participant_currency

        context.update({
            'invoices': all_invoices,
            'receipts': all_invoices,  # For backward compatibility
            'paid_count': paid_count,
            'unpaid_count': unpaid_count,
            'overdue_count': overdue_count,
            'cancelled_count': cancelled_count,
            'refunded_count': refunded_count,
            'unpaid_total': unpaid_total,
            'currency': participant_currency,
            'total_invoices': len(all_invoices),
            'participant': participant,
        })
        
        return context


class InvoiceDetailView(LoginRequiredMixin, TemplateView):
    """View for displaying a single invoice"""
    template_name = "payments/invoice_detail.html"
    login_url = "/auth/login/"
    
    def get(self, request, *args, **kwargs):
        """Override get to handle missing invoices gracefully"""
        invoice_id = self.kwargs.get('invoice_id')
        transaction_id = self.kwargs.get('transaction_id') or self.request.GET.get('transaction_id')
        
        # If invoice_id provided, check if it exists
        if invoice_id and not transaction_id:
            from payments.models import PaymentReceipt
            from appointments.models import Appointment
            from django.contrib import messages
            from django.shortcuts import render
            
            # Check if receipt exists
            if not PaymentReceipt.objects.filter(id=invoice_id).exists():
                # Check if appointment exists in any database
                appointment_exists = False
                for db in ['default', 'frankfurt']:
                    try:
                        if Appointment.objects.using(db).filter(id=invoice_id).exists():
                            appointment_exists = True
                            break
                    except Exception:
                        pass
                
                if not appointment_exists:
                    # Neither receipt nor appointment exists - show friendly error
                    messages.warning(request, 
                        "Cette facture n'est plus disponible. "
                        "Cela peut être dû à une migration de données récente. "
                        "Veuillez contacter le support si vous avez besoin d'une copie de cette facture."
                    )
                    return render(request, 'payments/invoice_not_found.html', {
                        'invoice_id': invoice_id,
                        'portal': request.path.split("/")[1] if len(request.path.split("/")) > 1 else 'patient'
                    })
        
        return super().get(request, *args, **kwargs)
    
    def _generate_receipt_from_appointment(self, appointment):
        """Generate a PaymentReceipt on-the-fly from appointment data"""
        from payments.models import PaymentReceipt
        from django.utils import timezone
        
        # Create receipt without saving to database (transient object)
        receipt = PaymentReceipt(
            id=appointment.id,  # Use appointment ID
            receipt_number=f"APT-{str(appointment.id)[:8].upper()}",
            issued_to=appointment.patient,
            issued_by=appointment.doctor if appointment.doctor else appointment.hospital,
            amount=appointment.final_price or appointment.consultation_fee or 0,
            currency=appointment.currency or 'XOF',
            payment_method=appointment.payment_method or 'onsite',
            payment_status=appointment.payment_status or 'pending',
            issued_at=appointment.created_at,
            description=f"Consultation - {appointment.appointment_type or 'General'}",
            metadata={
                'appointment_id': str(appointment.id),
                'appointment_date': str(appointment.appointment_date),
                'appointment_time': str(appointment.appointment_time),
                'doctor': appointment.doctor.full_name if appointment.doctor else 'N/A',
                'generated_on_fly': True,
            }
        )
        return receipt
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice_id = self.kwargs.get('invoice_id')
        transaction_id = self.kwargs.get('transaction_id') or self.request.GET.get('transaction_id')
        
        if transaction_id:
            receipt = get_object_or_404(
                PaymentReceipt,
                db_models.Q(service_transaction__id=transaction_id) | db_models.Q(transaction__id=transaction_id)
            )
        elif invoice_id:
            # Try to find receipt by ID first
            try:
                receipt = PaymentReceipt.objects.get(id=invoice_id)
            except PaymentReceipt.DoesNotExist:
                # If not found, try to find by appointment ID
                from appointments.models import Appointment
                
                try:
                    appointment = Appointment.objects.get(id=invoice_id)
                except Appointment.DoesNotExist:
                    from django.http import Http404
                    raise Http404("Invoice not found")
                
                # Find receipt linked to this appointment via Transaction
                from core.models import Transaction
                service_transaction = Transaction.objects.filter(
                    service_id=str(appointment.id)
                ).first()
                
                if service_transaction and hasattr(service_transaction, 'receipt'):
                    receipt = service_transaction.receipt
                else:
                    receipt = None
                
                if not receipt:
                    # Generate receipt on-the-fly from appointment data
                    receipt = self._generate_receipt_from_appointment(appointment)
        else:
            from django.http import Http404
            raise Http404("Invoice not found")
        
        if not receipt:
            from django.http import Http404
            raise Http404("Receipt could not be generated for this appointment")
        
        if receipt.issued_to != self.request.user and receipt.issued_by != self.request.user:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to view this invoice")
        
        receipt.ensure_invoice_data()

        portal = self.request.path.split("/")[1]
        context["portal"] = portal

        from currency_converter.services import CurrencyConverterService
        participant = self.request.user

        try:
            if participant.preferred_currency:
                participant_currency = participant.preferred_currency
            elif hasattr(participant, 'country') and participant.country:
                participant_currency = CurrencyConverterService.get_currency_from_country(participant.country)
            else:
                participant_currency = 'XOF'
        except Exception:
            participant_currency = 'XOF'

        # Convert receipt amounts to participant's currency
        receipt_currency = receipt.currency or 'XOF'

        # Convert line items
        if receipt.line_items:
            converted_line_items = []
            for item in receipt.line_items:
                item_amount = Decimal(str(item.get('amount', 0)))
                if receipt_currency != participant_currency:
                    converted_amount = CurrencyConverterService.convert_amount(
                        item_amount,
                        receipt_currency,
                        participant_currency
                    )
                else:
                    converted_amount = item_amount

                converted_item = item.copy()
                converted_item['amount'] = converted_amount
                converted_item['original_amount'] = item_amount
                converted_item['original_currency'] = receipt_currency
                converted_line_items.append(converted_item)
            receipt.converted_line_items = converted_line_items
        else:
            receipt.converted_line_items = []

        # Convert main amounts
        if receipt_currency != participant_currency:
            receipt.converted_total_amount = CurrencyConverterService.convert_amount(
                receipt.total_amount or Decimal('0'),
                receipt_currency,
                participant_currency
            )
            receipt.converted_subtotal = CurrencyConverterService.convert_amount(
                receipt.subtotal or Decimal('0'),
                receipt_currency,
                participant_currency
            )
            receipt.converted_amount = CurrencyConverterService.convert_amount(
                receipt.amount or Decimal('0'),
                receipt_currency,
                participant_currency
            )
            receipt.converted_tax_amount = CurrencyConverterService.convert_amount(
                receipt.tax_amount or Decimal('0'),
                receipt_currency,
                participant_currency
            ) if receipt.tax_amount else None
            receipt.converted_platform_fee = CurrencyConverterService.convert_amount(
                receipt.platform_fee or Decimal('0'),
                receipt_currency,
                participant_currency
            ) if receipt.platform_fee else None
            receipt.converted_discount_amount = CurrencyConverterService.convert_amount(
                receipt.discount_amount or Decimal('0'),
                receipt_currency,
                participant_currency
            ) if receipt.discount_amount else None
        else:
            receipt.converted_total_amount = receipt.total_amount or Decimal('0')
            receipt.converted_subtotal = receipt.subtotal or Decimal('0')
            receipt.converted_amount = receipt.amount or Decimal('0')
            receipt.converted_tax_amount = receipt.tax_amount
            receipt.converted_platform_fee = receipt.platform_fee
            receipt.converted_discount_amount = receipt.discount_amount

        receipt.display_currency = participant_currency
        receipt.original_currency = receipt_currency

        context.update({
            'receipt': receipt,
            'invoice_number': receipt.invoice_number or receipt.receipt_number,
            'company_ifu': getattr(settings, 'COMPANY_IFU', 'N/A'),
            'company_phone': getattr(settings, 'COMPANY_PHONE', '+229 XX XX XX XX'),
            'company_address': getattr(settings, 'COMPANY_ADDRESS', 'Cotonou, BENIN'),
            'participant_currency': participant_currency,
            'currency_service': CurrencyConverterService,
        })
        
        return context


class InvoiceDownloadView(LoginRequiredMixin, TemplateView):
    """View for downloading invoice PDF"""
    
    def get(self, request, *args, **kwargs):
        invoice_id = self.kwargs.get('invoice_id')
        
        receipt = get_object_or_404(
            PaymentReceipt,
            id=invoice_id
        )
        
        if receipt.issued_to != request.user and receipt.issued_by != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        try:
            pdf_buffer = EnhancedReceiptService.generate_invoice_receipt(
                receipt,
                receipt.service_transaction
            )
            
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            filename = f"facture_{receipt.invoice_number or receipt.receipt_number}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class MarkOnsitePaymentPaidView(LoginRequiredMixin, TemplateView):
    """API endpoint for service providers to mark onsite payments as paid"""
    
    def post(self, request, *args, **kwargs):
        from django.views.decorators.csrf import csrf_exempt
        from django.utils.decorators import method_decorator
        import json
        
        participant = request.user
        
        if participant.role not in ['doctor', 'hospital', 'pharmacy', 'insurance_company']:
            return JsonResponse({'error': 'Only service providers can mark payments as paid'}, status=403)
        
        try:
            data = json.loads(request.body)
            transaction_id = data.get('transaction_id')
            
            if not transaction_id:
                return JsonResponse({'error': 'transaction_id is required'}, status=400)
            
            service_txn = get_object_or_404(
                ServiceTransaction,
                id=transaction_id,
                service_provider=participant
            )
            
            if service_txn.payment_method != 'onsite_cash':
                return JsonResponse({
                    'error': 'Only onsite cash payments can be marked as paid manually'
                }, status=400)
            
            if service_txn.status == 'completed':
                return JsonResponse({
                    'error': 'This payment is already marked as paid'
                }, status=400)
            
            service_txn.status = 'completed'
            service_txn.payment_date = timezone.now()
            service_txn.save()
            
            receipt = PaymentReceipt.objects.filter(service_transaction=service_txn).first()
            if receipt:
                receipt.payment_status = 'PAID'
                receipt.payment_date = timezone.now()
                receipt.save()
                
                core_txn = receipt.transaction
                if core_txn and core_txn.status == 'pending':
                    core_txn.status = 'completed'
                    core_txn.completed_at = timezone.now()
                    core_txn.save()
                    
                    from appointments.models import Appointment
                    appointment = Appointment.objects.filter(payment_id=core_txn.id).first()
                    if appointment:
                        appointment.payment_status = 'paid'
                        appointment.status = 'confirmed'
                        appointment.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Payment marked as paid successfully',
                'transaction_id': str(service_txn.id),
                'status': service_txn.status
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class VerifyInvoiceQRView(LoginRequiredMixin, TemplateView):
    """API endpoint to verify invoice QR code"""
    
    def post(self, request, *args, **kwargs):
        import json
        from .qr_service import QRCodeService
        
        try:
            data = json.loads(request.body)
            qr_data = data.get('qr_data')
            
            if not qr_data:
                return JsonResponse({'error': 'qr_data is required'}, status=400)
            
            result = QRCodeService.verify_qr_data(qr_data)
            
            if not result.get('valid'):
                return JsonResponse(result, status=400)
            
            receipt = result['receipt']
            
            return JsonResponse({
                'valid': True,
                'invoice_number': result['invoice_number'],
                'amount': str(result['amount']),
                'currency': result['currency'],
                'status': result['status'],
                'patient_name': result['patient_name'],
                'issued_at': result['issued_at'].isoformat() if result['issued_at'] else None,
                'can_mark_paid': (
                    request.user.role in ['doctor', 'hospital', 'pharmacy', 'insurance_company'] and
                    receipt.service_transaction and
                    receipt.service_transaction.service_provider == request.user and
                    receipt.service_transaction.payment_method == 'onsite_cash' and
                    receipt.payment_status == 'PENDING'
                )
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class ServiceProviderWalletView(LoginRequiredMixin, TemplateView):
    """Wallet view for service participants (doctor, hospital, pharmacy, insurance_company)"""
    template_name = "payments/service_participant_wallet.html"
    login_url = "/auth/login/"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        participant = self.request.user
        
        if participant.role not in ['doctor', 'hospital', 'pharmacy', 'insurance_company']:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Only doctors, hospitals, pharmacies, and insurance companies can access this page")
        
        portal = self.request.path.split("/")[1]
        context["portal"] = portal
        
        from .models import ServiceTransaction, TransactionFee, PayoutSchedule, ParticipantGatewayAccount
        
        completed_txns = ServiceTransaction.objects.filter(
            service_provider=participant,
            status='completed'
        ).select_related('fee_details', 'gateway_transaction', 'patient')
        
        total_gross = completed_txns.aggregate(
            total=db_models.Sum('amount')
        )['total'] or Decimal('0')
        
        total_net = Decimal('0')
        total_fees = Decimal('0')
        for txn in completed_txns:
            if hasattr(txn, 'fee_details') and txn.fee_details:
                total_net += txn.fee_details.net_amount_to_provider
                total_fees += txn.fee_details.total_fee_amount
            else:
                total_net += txn.amount
        
        pending_txns = ServiceTransaction.objects.filter(
            service_provider=participant,
            status__in=['pending', 'processing']
        )
        
        pending_amount = pending_txns.aggregate(
            total=db_models.Sum('amount')
        )['total'] or Decimal('0')
        
        recent_transactions = ServiceTransaction.objects.filter(
            service_provider=participant
        ).select_related(
            'patient', 'gateway_transaction', 'fee_details'
        ).order_by('-created_at')[:20]
        
        pending_payouts = PayoutSchedule.objects.filter(
            participant=participant,
            payout_status__in=['scheduled', 'processing']
        ).order_by('-scheduled_for')
        
        completed_payouts = PayoutSchedule.objects.filter(
            participant=participant,
            payout_status='completed'
        ).order_by('-processed_at')[:10]
        
        gateway_accounts = ParticipantGatewayAccount.objects.filter(
            participant=participant
        ).order_by('-is_default', '-created_at')

        # Get participant's preferred currency
        from currency_converter.services import CurrencyConverterService
        try:
            if participant.preferred_currency:
                participant_currency = participant.preferred_currency
            elif hasattr(participant, 'country') and participant.country:
                participant_currency = CurrencyConverterService.get_currency_from_country(participant.country)
            else:
                participant_currency = 'XOF'
        except Exception:
            participant_currency = 'XOF'

        context.update({
            'total_gross': total_gross,
            'total_net': total_net,
            'total_fees': total_fees,
            'pending_amount': pending_amount,
            'pending_count': pending_txns.count(),
            'transactions': recent_transactions,
            'pending_payouts': pending_payouts,
            'completed_payouts': completed_payouts,
            'gateway_accounts': gateway_accounts,
            'currency': participant_currency,
        })
        
        return context
