from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import render
from django.utils import timezone
from django.db import transaction
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
import uuid
from .models import *
from .service_models import InsuranceService
from .serializers import *
from core.services import WalletService
from communication.notification_service import NotificationService


class InsurancePackageViewSet(viewsets.ModelViewSet):  # View for InsurancePackageSet operations
    serializer_class = InsurancePackageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return InsurancePackage.objects.none()
        if self.request.user.role == 'insurance_company':
            return InsurancePackage.objects.filter(company=self.request.user).order_by("-created_at")
        return InsurancePackage.objects.filter(is_active=True).order_by("company__full_name", "name")

    def perform_create(self, serializer):  # Perform create
        if self.request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can create packages")
        serializer.save(company=self.request.user)

    def perform_update(self, serializer):  # Perform update
        if self.request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can update packages")
        if serializer.instance.company != self.request.user:
            raise PermissionDenied("You can only update your own packages")
        serializer.save()

    def perform_destroy(self, instance):  # Perform destroy
        if self.request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can delete packages")
        if instance.company != self.request.user:
            raise PermissionDenied("You can only delete your own packages")
        instance.delete()

    @action(detail=False, methods=["get"])
    def my_subscriptions(self, request):
        """Get all active insurance subscriptions for the patient"""
        try:
            subscriptions = (
                InsuranceSubscription.objects.filter(patient=request.user)
                .select_related("insurance_package__company", "insurance_card")
                .order_by("-created_at")
            )

            serializer = InsuranceSubscriptionSerializer(subscriptions, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"])
    def current_card(self, request):  # Current card
        try:
            card = (
                PatientInsuranceCard.objects.filter(
                    patient=request.user, status="active"
                )
                .select_related("insurance_package__company")
                .first()
            )

            if card:
                serializer = PatientInsuranceCardSerializer(card)
                return Response(serializer.data)
            return Response(
                {"message": "No active insurance card"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def calculate_next_payment_date(self, start_date, frequency):
        """Calculate next payment date based on frequency"""
        if frequency == "monthly":
            return start_date + relativedelta(months=1)
        elif frequency == "quarterly":
            return start_date + relativedelta(months=3)
        elif frequency == "semi_annual":
            return start_date + relativedelta(months=6)
        elif frequency == "annual":
            return start_date + relativedelta(years=1)
        return start_date + relativedelta(months=1)  # Default to monthly

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def subscribe(self, request, pk=None):
        """Subscribe to insurance package with payment"""
        try:
            package = self.get_object()
            payment_method = request.data.get("payment_method", "wallet")

            # Check if patient already has this package
            existing_sub = InsuranceSubscription.objects.filter(
                patient=request.user, insurance_package=package, status="active"
            ).exists()

            if existing_sub:
                return Response(
                    {
                        "error": f"You already have an active subscription to {package.name}"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            today = timezone.now().date()
            next_payment = self.calculate_next_payment_date(
                today, package.payment_frequency
            )

            # Process initial payment
            try:
                payment_result = WalletService.make_payment(
                    patient=request.user,
                    recipient=package.company,  # Payment goes to insurance company
                    amount=package.premium_amount,
                    description=f"Insurance Premium - {package.name} ({package.get_payment_frequency_display()})",
                    payment_method=payment_method,
                    metadata={
                        "insurance_package_id": str(package.id),
                        "insurance_package_name": package.name,
                        "company_name": package.company.full_name,
                        "payment_frequency": package.payment_frequency,
                        "type": "insurance_premium_initial",
                    },
                )

                transaction_ref = payment_result["patient_transaction"].transaction_ref

            except ValueError as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except Exception as e:
                return Response(
                    {"error": "Payment processing failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Create insurance card
            card = PatientInsuranceCard.objects.create(
                patient=request.user,
                insurance_package=package,
                card_number=f"INS-{uuid.uuid4().hex[:12].upper()}",
                policy_number=f"POL-{uuid.uuid4().hex[:10].upper()}",
                status="active",
                issue_date=today,
                expiry_date=today + timedelta(days=365),
                coverage_start_date=today,
                coverage_end_date=today + timedelta(days=365),
            )

            # Create subscription
            subscription = InsuranceSubscription.objects.create(
                patient=request.user,
                insurance_package=package,
                insurance_card=card,
                status="active",
                start_date=today,
                next_payment_date=next_payment,
                last_payment_date=today,
                premium_amount=package.premium_amount,
                payment_frequency=package.payment_frequency,
                total_paid=package.premium_amount,
                payment_count=1,
                auto_renew=True,
                payment_method=payment_method,
            )

            # Create first invoice
            invoice = InsuranceInvoice.objects.create(
                invoice_number=f"INV-{uuid.uuid4().hex[:10].upper()}",
                subscription=subscription,
                patient=request.user,
                insurance_package=package,
                amount=package.premium_amount,
                status="paid",
                issue_date=today,
                due_date=today,
                paid_date=today,
                transaction_ref=str(transaction_ref),
                payment_method=payment_method,
                period_start=today,
                period_end=next_payment - timedelta(days=1),
            )

            serializer = InsuranceSubscriptionSerializer(subscription)
            return Response(
                {
                    "success": True,
                    "message": f"Successfully subscribed to {package.name}",
                    "subscription": serializer.data,
                    "transaction_ref": str(transaction_ref),
                    "invoice_number": invoice.invoice_number,
                    "next_payment_date": str(next_payment),
                    "amount_paid": package.premium_amount,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def cancel_subscription(self, request):
        """Cancel an active subscription"""
        try:
            subscription_id = request.data.get("subscription_id")
            reason = request.data.get("reason", "Patient requested cancellation")

            subscription = InsuranceSubscription.objects.get(
                id=subscription_id, patient=request.user
            )

            if subscription.status != "active":
                return Response(
                    {"error": "Subscription is not active"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            subscription.status = "cancelled"
            subscription.cancellation_reason = reason
            subscription.cancelled_at = timezone.now()
            subscription.end_date = timezone.now().date()
            subscription.save()

            # Update insurance card
            if subscription.insurance_card:
                subscription.insurance_card.status = "inactive"
                subscription.insurance_card.save()

            return Response(
                {
                    "success": True,
                    "message": "Subscription cancelled successfully",
                }
            )

        except InsuranceSubscription.DoesNotExist:
            return Response(
                {"error": "Subscription not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InsuranceSubscriptionViewSet(viewsets.ModelViewSet):  # View for InsuranceSubscriptionSet operations
    serializer_class = InsuranceSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return InsuranceSubscription.objects.none()
        if self.request.user.role == 'insurance_company':
            return InsuranceSubscription.objects.filter(
                insurance_package__company=self.request.user
            ).select_related('patient', 'insurance_package', 'insurance_card').order_by('-created_at')
        return InsuranceSubscription.objects.filter(patient=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending subscription and activate the insurance card"""
        subscription = self.get_object()

        if subscription.status != 'pending_approval':
            return Response(
                {'error': 'Only pending subscriptions can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )

        approval_notes = request.data.get('approval_notes', '')

        subscription.status = 'active'
        subscription.approved_by = request.user
        subscription.approved_at = timezone.now()
        subscription.approval_notes = approval_notes
        subscription.save()

        # Activate the insurance card if it exists
        if subscription.insurance_card:
            subscription.insurance_card.status = 'active'
            subscription.insurance_card.save()

        serializer = self.get_serializer(subscription)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign a subscription to a staff member for review"""
        subscription = self.get_object()

        staff_id = request.data.get('staff_id')
        if not staff_id:
            return Response(
                {'error': 'staff_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            staff = Participant.objects.get(id=staff_id)
        except Participant.DoesNotExist:
            return Response(
                {'error': 'Staff member not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        subscription.assigned_to = staff
        subscription.save()

        serializer = self.get_serializer(subscription)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a pending subscription"""
        subscription = self.get_object()

        if subscription.status != 'pending_approval':
            return Response(
                {'error': 'Only pending subscriptions can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rejection_reason = request.data.get('rejection_reason', '')
        if not rejection_reason:
            return Response(
                {'error': 'rejection_reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription.status = 'cancelled'
        subscription.cancellation_reason = rejection_reason
        subscription.cancelled_at = timezone.now()
        subscription.save()

        serializer = self.get_serializer(subscription)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_payment_reminder(self, request, pk=None):
        """Send payment reminder to patient for overdue subscription payment"""
        subscription = self.get_object()

        if subscription.status != 'active':
            return Response(
                {'error': 'Can only send reminders for active subscriptions'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if payment is due or overdue
        if not subscription.next_payment_date:
            return Response(
                {'error': 'No payment date scheduled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # TODO: Implement actual notification sending
        # This should:
        # 1. Check participant preferences for notification channels
        # 2. Send email/SMS based on preferences
        # 3. Log the notification

        # For now, return success
        return Response({
            'message': 'Payment reminder sent successfully',
            'patient': subscription.patient.full_name,
            'amount': subscription.premium_amount,
            'due_date': subscription.next_payment_date
        })


class InsuranceInvoiceViewSet(viewsets.ModelViewSet):  # View for InsuranceInvoiceSet operations
    serializer_class = InsuranceInvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return InsuranceInvoice.objects.none()
        if self.request.user.role == 'insurance_company':
            return InsuranceInvoice.objects.filter(
                insurance_package__company=self.request.user
            ).select_related('patient', 'subscription', 'insurance_package').order_by('-issue_date')
        return InsuranceInvoice.objects.filter(patient=self.request.user).order_by('-issue_date')
    
    @action(detail=True, methods=['post'])
    def pay_with_wallet(self, request, pk=None):
        """Pay insurance invoice from patient wallet"""
        try:
            invoice = self.get_object()
            if invoice.patient != request.user:
                raise PermissionDenied("You can only pay your own invoices")
            if invoice.status == 'paid':
                return Response({'error': 'Invoice already paid'}, status=status.HTTP_400_BAD_REQUEST)
            
            from .payment_service import InsurancePaymentService
            result = InsurancePaymentService.process_wallet_payment(invoice=invoice, patient=request.user)
            
            if result['success']:
                serializer = self.get_serializer(invoice)
                return Response({'success': True, 'message': 'Payment successful', 'new_balance': result['new_balance'], **serializer.data})
            else:
                return Response({'error': result.get('error', 'Payment failed')}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def pay_with_fedapay(self, request, pk=None):
        """Initiate FedaPay payment for insurance invoice"""
        try:
            invoice = self.get_object()
            if invoice.patient != request.user:
                raise PermissionDenied("You can only pay your own invoices")
            if invoice.status == 'paid':
                return Response({'error': 'Invoice already paid'}, status=status.HTTP_400_BAD_REQUEST)
            
            from .payment_service import InsurancePaymentService
            callback_url = request.data.get('callback_url', request.build_absolute_uri('/patient/insurance/invoices/'))
            result = InsurancePaymentService.initiate_fedapay_payment(invoice=invoice, patient=request.user, callback_url=callback_url)
            
            if result['success']:
                return Response({'success': True, 'payment_url': result['payment_url'], 'payment_token': result['payment_token'], 'transaction_id': result['transaction_id']})
            else:
                return Response({'error': result.get('error', 'Failed to initiate payment')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InsuranceClaimViewSet(viewsets.ModelViewSet):  # View for InsuranceClaimSet operations
    serializer_class = InsuranceClaimSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return InsuranceClaim.objects.none()
        if self.request.user.role == 'insurance_company':
            return InsuranceClaim.objects.filter(
                insurance_package__company=self.request.user
            ).select_related('patient', 'insurance_card', 'insurance_package').order_by('-submission_date')
        return InsuranceClaim.objects.filter(patient=self.request.user).order_by('-submission_date')

    @transaction.atomic
    def create(self, request, *args, **kwargs):  # Create
        try:
            data = request.data
            
            # Check for idempotency
            idempotency_key = request.META.get('HTTP_IDEMPOTENCY_KEY') or data.get('idempotency_key')
            if idempotency_key:
                existing_claim = InsuranceClaim.objects.filter(idempotency_key=idempotency_key).first()
                if existing_claim:
                    serializer = self.get_serializer(existing_claim)
                    return Response(
                        {
                            'success': True,
                            'message': 'Claim already exists',
                            'claim_number': existing_claim.claim_number,
                            **serializer.data
                        },
                        status=status.HTTP_200_OK
                    )
            
            insurance_card_id = data.get('insurance_card_id')

            try:
                insurance_card = PatientInsuranceCard.objects.get(
                    id=insurance_card_id,
                    patient=request.user,
                    status='active'
                )
            except PatientInsuranceCard.DoesNotExist:
                return Response(
                    {'error': 'Active insurance card not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get or create healthcare provider participant if name is provided
            healthcare_provider = None
            provider_name = data.get('partner_name') or data.get('provider_name')
            provider_id = data.get('partner_id') or data.get('provider_id')
            
            if provider_id:
                try:
                    healthcare_provider = Participant.objects.get(uid=provider_id)
                except Participant.DoesNotExist:
                    pass
            
            claim = InsuranceClaim.objects.create(
                claim_number=f"CLM-{uuid.uuid4().hex[:10].upper()}",
                idempotency_key=idempotency_key,
                patient=request.user,
                insurance_card=insurance_card,
                insurance_package=insurance_card.insurance_package,
                service_type=data.get('service_type'),
                healthcare_provider=healthcare_provider,
                service_date=data.get('service_date'),
                claimed_amount=data.get('claimed_amount'),
                diagnosis=data.get('diagnosis', ''),
                treatment_details=data.get('treatment_details', ''),
                status='submitted'
            )

            # Get patient's currency for display
            from currency_converter.services import CurrencyConverterService
            patient_currency = CurrencyConverterService.get_participant_currency(request.user)

            # Notify insurance company about new claim
            NotificationService.create_notification(
                recipient=insurance_card.insurance_package.company,
                notification_type='insurance',
                title='Nouvelle réclamation',
                message=f'Nouvelle réclamation de {request.user.full_name} - Montant: {data.get("claimed_amount")} {patient_currency}',
                action_url=f'/insurance/claims/',
                metadata={'claim_id': str(claim.id), 'claim_number': claim.claim_number}
            )

            serializer = self.get_serializer(claim)
            return Response(
                {
                    'success': True,
                    'message': 'Claim submitted successfully',
                    'claim_number': claim.claim_number,
                    **serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):  # Review
        if request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can review claims")
        
        try:
            claim = self.get_object()
            if claim.insurance_package.company != request.user:
                raise PermissionDenied("You can only review claims for your packages")
            
            reviewer_notes = request.data.get('reviewer_notes', '')
            claim.status = 'underReview'
            claim.reviewer_notes = reviewer_notes
            claim.review_date = timezone.now()
            claim.save()
            
            serializer = self.get_serializer(claim)
            return Response({
                'success': True,
                'message': 'Claim moved to under review',
                **serializer.data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):  # Approve
        if request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can approve claims")
        
        try:
            claim = self.get_object()
            if claim.insurance_package.company != request.user:
                raise PermissionDenied("You can only approve claims for your packages")
            
            approved_amount = int(request.data.get('approved_amount', claim.claimed_amount))
            reviewer_notes = request.data.get('reviewer_notes', '')
            
            claim.status = 'approved'
            claim.approved_amount = approved_amount
            claim.reviewer_notes = reviewer_notes
            claim.approval_date = timezone.now()
            claim.save()

            # Get patient's currency for display
            from currency_converter.services import CurrencyConverterService
            patient_currency = CurrencyConverterService.get_participant_currency(claim.patient)

            # Notify patient about approval
            NotificationService.create_notification(
                recipient=claim.patient,
                notification_type='insurance',
                title='Réclamation approuvée',
                message=f'Votre réclamation #{claim.claim_number} a été approuvée. Montant approuvé: {approved_amount} {patient_currency}',
                action_url=f'/patient/insurance/claims/',
                metadata={'claim_id': str(claim.id), 'claim_number': claim.claim_number}
            )

            serializer = self.get_serializer(claim)
            return Response({
                'success': True,
                'message': f'Claim approved for {approved_amount} {patient_currency}',
                **serializer.data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):  # Reject
        if request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can reject claims")
        
        try:
            claim = self.get_object()
            if claim.insurance_package.company != request.user:
                raise PermissionDenied("You can only reject claims for your packages")
            
            rejection_reason = request.data.get('rejection_reason', '')
            if not rejection_reason:
                return Response({'error': 'Rejection reason is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            claim.status = 'rejected'
            claim.rejection_reason = rejection_reason
            claim.reviewer_notes = request.data.get('reviewer_notes', '')
            claim.save()
            
            # Notify patient about rejection
            NotificationService.create_notification(
                recipient=claim.patient,
                notification_type='insurance',
                title='Réclamation rejetée',
                message=f'Votre réclamation #{claim.claim_number} a été rejetée. Raison: {rejection_reason}',
                action_url=f'/patient/insurance/claims/',
                metadata={'claim_id': str(claim.id), 'claim_number': claim.claim_number}
            )
            
            serializer = self.get_serializer(claim)
            return Response({
                'success': True,
                'message': 'Claim rejected',
                **serializer.data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def mark_paid(self, request, pk=None):  # Mark paid
        if request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can mark claims as paid")
        
        try:
            claim = self.get_object()
            if claim.insurance_package.company != request.user:
                raise PermissionDenied("You can only mark claims as paid for your packages")
            
            if claim.status != 'approved':
                return Response(
                    {'error': 'Claim must be approved before marking as paid'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check for conflicting refunds
            from core.models import RefundRequest
            conflicting_refunds = RefundRequest.objects.filter(
                insurance_claim=claim,
                status__in=['completed', 'processing', 'approved']
            )
            if conflicting_refunds.exists():
                return Response(
                    {'error': 'Cannot pay claim - a refund request is already processed or in progress for this claim'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process reimbursement
            from .payment_service import InsurancePaymentService
            
            result = InsurancePaymentService.process_claim_reimbursement(
                claim=claim,
                approved_amount=claim.approved_amount
            )
            
            if result['success']:
                # Get patient's currency for display
                from currency_converter.services import CurrencyConverterService
                patient_currency = CurrencyConverterService.get_participant_currency(claim.patient)

                serializer = self.get_serializer(claim)
                return Response({
                    'success': True,
                    'message': f'Reimbursement of {claim.approved_amount} {patient_currency} sent to patient',
                    **serializer.data
                })
            else:
                return Response(
                    {'error': result.get('error', 'Failed to process reimbursement')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can mark claims as paid")
        
        try:
            claim = self.get_object()
            if claim.insurance_package.company != request.user:
                raise PermissionDenied("You can only mark your claims as paid")
            
            if claim.status != 'approved':
                return Response({'error': 'Only approved claims can be marked as paid'}, status=status.HTTP_400_BAD_REQUEST)
            
            paid_amount = int(request.data.get('paid_amount', claim.approved_amount))
            
            claim.status = 'paid'
            claim.paid_amount = paid_amount
            claim.payment_date = timezone.now()
            claim.save()

            # Get patient's currency for display
            from currency_converter.services import CurrencyConverterService
            patient_currency = CurrencyConverterService.get_participant_currency(claim.patient)

            serializer = self.get_serializer(claim)
            return Response({
                'success': True,
                'message': f'Claim marked as paid: {paid_amount} {patient_currency}',
                **serializer.data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InsuranceCoverageEnquiryViewSet(viewsets.ModelViewSet):  # View for InsuranceCoverageEnquirySet operations
    serializer_class = InsuranceCoverageEnquirySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return InsuranceCoverageEnquiry.objects.none()
        if self.request.user.role == 'insurance_company':
            return InsuranceCoverageEnquiry.objects.filter(
                insurance_package__company=self.request.user
            ).select_related('patient', 'insurance_card', 'insurance_package').order_by('-created_at')
        return InsuranceCoverageEnquiry.objects.filter(patient=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):  # Create
        try:
            data = request.data
            insurance_card_id = data.get('insurance_card_id')

            try:
                insurance_card = PatientInsuranceCard.objects.get(
                    id=insurance_card_id,
                    patient=request.user,
                    status='active'
                )
            except PatientInsuranceCard.DoesNotExist:
                return Response(
                    {'error': 'Active insurance card not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get healthcare provider participant if provided
            healthcare_provider = None
            provider_name = data.get('partner_name') or data.get('provider_name')
            provider_id = data.get('partner_id') or data.get('provider_id')
            
            if provider_id:
                try:
                    healthcare_provider = Participant.objects.get(uid=provider_id)
                except Participant.DoesNotExist:
                    pass
            
            enquiry = InsuranceCoverageEnquiry.objects.create(
                enquiry_number=f"ENQ-{uuid.uuid4().hex[:10].upper()}",
                patient=request.user,
                insurance_card=insurance_card,
                insurance_package=insurance_card.insurance_package,
                service_type=data.get('service_type'),
                service_name=data.get('service_name'),
                service_description=data.get('service_description'),
                estimated_cost=int(data.get('estimated_cost')),
                healthcare_provider=healthcare_provider,
                planned_date=data.get('planned_date'),
                medical_necessity=data.get('medical_necessity'),
                doctor_recommendation=data.get('doctor_recommendation', ''),
                status='pending'
            )

            serializer = self.get_serializer(enquiry)
            return Response(
                {
                    'success': True,
                    'message': 'Coverage enquiry submitted successfully',
                    'enquiry_number': enquiry.enquiry_number,
                    **serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):  # Review
        if request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can review enquiries")
        
        try:
            enquiry = self.get_object()
            if enquiry.insurance_package.company != request.user:
                raise PermissionDenied("You can only review enquiries for your packages")
            
            enquiry.status = 'under_review'
            enquiry.reviewed_by = request.user
            enquiry.reviewed_at = timezone.now()
            enquiry.save()
            
            serializer = self.get_serializer(enquiry)
            return Response({
                'success': True,
                'message': 'Enquiry moved to under review',
                **serializer.data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):  # Approve
        if request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can approve enquiries")
        
        try:
            enquiry = self.get_object()
            if enquiry.insurance_package.company != request.user:
                raise PermissionDenied("You can only approve enquiries for your packages")
            
            coverage_percentage = float(request.data.get('coverage_percentage', 0))
            approval_notes = request.data.get('approval_notes', '')
            conditions = request.data.get('conditions', '')
            validity_days = int(request.data.get('validity_days', 30))
            
            insurance_covers = int(enquiry.estimated_cost * (coverage_percentage / 100))
            patient_pays = enquiry.estimated_cost - insurance_covers
            
            enquiry.status = 'approved'
            enquiry.insurance_coverage_percentage = coverage_percentage
            enquiry.insurance_covers_amount = insurance_covers
            enquiry.patient_pays_amount = patient_pays
            enquiry.approval_notes = approval_notes
            enquiry.conditions = conditions
            enquiry.reviewed_by = request.user
            enquiry.reviewed_at = timezone.now()
            enquiry.expires_at = timezone.now() + timedelta(days=validity_days)
            enquiry.save()

            # Get patient's currency for display
            from currency_converter.services import CurrencyConverterService
            patient_currency = CurrencyConverterService.get_participant_currency(enquiry.patient)

            serializer = self.get_serializer(enquiry)
            return Response({
                'success': True,
                'message': f'Enquiry approved: Insurance covers {coverage_percentage}% ({insurance_covers} {patient_currency})',
                **serializer.data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):  # Reject
        if request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can reject enquiries")
        
        try:
            enquiry = self.get_object()
            if enquiry.insurance_package.company != request.user:
                raise PermissionDenied("You can only reject enquiries for your packages")
            
            rejection_reason = request.data.get('rejection_reason', '')
            if not rejection_reason:
                return Response({'error': 'Rejection reason is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            enquiry.status = 'rejected'
            enquiry.rejection_reason = rejection_reason
            enquiry.reviewed_by = request.user
            enquiry.reviewed_at = timezone.now()
            enquiry.save()

            serializer = self.get_serializer(enquiry)
            return Response({
                'success': True,
                'message': 'Enquiry rejected',
                **serializer.data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InsuranceStaffViewSet(viewsets.ModelViewSet):  # View for InsuranceStaffSet operations
    serializer_class = InsuranceStaffSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return InsuranceStaff.objects.none()
        if self.request.user.role == 'insurance_company':
            return InsuranceStaff.objects.filter(
                insurance_company=self.request.user
            ).select_related('staff_participant', 'supervisor').order_by('-created_at')
        return InsuranceStaff.objects.none()

    def create(self, request, *args, **kwargs):
        """Create a new staff member"""
        try:
            data = request.data

            # Create the participant account for the staff
            staff_email = data.get('email')
            staff_name = data.get('full_name')
            staff_phone = data.get('phone_number', '')

            # Check if participant already exists
            try:
                staff_participant = Participant.objects.get(email=staff_email)
                if hasattr(staff_participant, 'insurance_staff_profile'):
                    return Response(
                        {'error': 'This email is already registered as a staff member'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Participant.DoesNotExist:
                # Create new participant - use insurance_company role, not insurance_company_staff
                staff_participant = Participant.objects.create(
                    email=staff_email,
                    full_name=staff_name,
                    phone_number=staff_phone,
                    role='insurance_company',
                    staff_role=data.get('staff_role'),  # Set staff_role to differentiate from owner
                    affiliated_provider_id=request.user.uid,  # Link to insurance company
                    is_active=True,
                )
                # Set a temporary password (should be sent via email)
                temp_password = Participant.objects.make_random_password()
                staff_participant.set_password(temp_password)
                staff_participant.save()

            # Create the InsuranceStaff profile
            staff = InsuranceStaff.objects.create(
                staff_participant=staff_participant,
                insurance_company=request.user,
                staff_role=data.get('staff_role'),
                department=data.get('department', ''),
                employee_id=data.get('employee_id', ''),
                permissions=data.get('permissions', []),
                supervisor_id=data.get('supervisor_id') if data.get('supervisor_id') else None,
            )

            serializer = self.get_serializer(staff)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a staff member"""
        staff = self.get_object()
        staff.is_active = False
        staff.termination_date = timezone.now().date()
        staff.save()

        # Also deactivate the participant account
        staff.staff_participant.is_active = False
        staff.staff_participant.save()

        serializer = self.get_serializer(staff)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """Reactivate a staff member"""
        staff = self.get_object()
        staff.is_active = True
        staff.termination_date = None
        staff.save()

        # Also reactivate the participant account
        staff.staff_participant.is_active = True
        staff.staff_participant.save()

        serializer = self.get_serializer(staff)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_permissions(self, request, pk=None):
        """Update staff permissions"""
        staff = self.get_object()
        permissions = request.data.get('permissions', [])
        staff.permissions = permissions
        staff.save()

        serializer = self.get_serializer(staff)
        return Response(serializer.data)


class HealthcarePartnerNetworkViewSet(viewsets.ModelViewSet):  # View for managing healthcare partner network
    serializer_class = HealthcarePartnerNetworkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return HealthcarePartnerNetwork.objects.none()
        if self.request.user.role == 'insurance_company':
            return HealthcarePartnerNetwork.objects.filter(
                insurance_company=self.request.user
            ).select_related('healthcare_partner', 'insurance_package').order_by('-created_at')
        return HealthcarePartnerNetwork.objects.none()

    def perform_create(self, serializer):  # Perform create
        if self.request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can add partners")
        serializer.save(insurance_company=self.request.user)

    def perform_update(self, serializer):  # Perform update
        if self.request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can update partners")
        if serializer.instance.insurance_company != self.request.user:
            raise PermissionDenied("You can only update your own network partners")
        serializer.save()

    def perform_destroy(self, instance):  # Perform destroy
        if self.request.user.role != 'insurance_company':
            raise PermissionDenied("Only insurance companies can remove partners")
        if instance.insurance_company != self.request.user:
            raise PermissionDenied("You can only remove your own network partners")
        instance.delete()

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get network partners grouped by type (hospital, clinic, pharmacy)"""
        partners = self.get_queryset()

        result = {
            'hospital': [],
            'clinic': [],
            'pharmacy': [],
            'laboratory': [],
            'other': []
        }

        for partner in partners:
            partner_data = self.get_serializer(partner).data
            partner_type = partner.healthcare_partner.role

            if partner_type in result:
                result[partner_type].append(partner_data)
            else:
                result['other'].append(partner_data)

        return Response(result)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a partner in the network"""
        partner = self.get_object()
        partner.status = 'active'
        partner.save()

        serializer = self.get_serializer(partner)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend a partner in the network"""
        partner = self.get_object()
        partner.status = 'suspended'
        partner.save()

        serializer = self.get_serializer(partner)
        return Response(serializer.data)


class InsuranceServiceViewSet(viewsets.ModelViewSet):
    """CRUD operations for insurance services with currency conversion"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return InsuranceService.objects.none()
        if self.request.user.role == 'insurance_company':
            return InsuranceService.objects.filter(insurance_company=self.request.user)
        return InsuranceService.objects.none()
    
    @transaction.atomic
    def perform_create(self, serializer):
        from currency_converter.utils import convert_to_xof
        
        insurance_company = self.request.user
        if not insurance_company.is_verified:
            raise PermissionDenied("Votre compte doit être vérifié pour créer des services")
        
        premium_input = self.request.data.get('premium_amount', 0)
        coverage_input = self.request.data.get('coverage_limit', 0)
        currency_input = self.request.data.get('currency', 'XOF')
        
        premium_in_xof_cents = convert_to_xof(premium_input, currency_input)
        coverage_in_xof_cents = convert_to_xof(coverage_input, currency_input) if coverage_input else None
        
        serializer.save(
            insurance_company=insurance_company,
            premium_amount=premium_in_xof_cents,
            coverage_limit=coverage_in_xof_cents,
            currency='XOF',
            region_code=insurance_company.region_code or 'global'
        )
    
    @transaction.atomic
    def perform_update(self, serializer):
        from currency_converter.utils import convert_to_xof
        
        if 'premium_amount' in self.request.data or 'coverage_limit' in self.request.data:
            premium_input = self.request.data.get('premium_amount', 0)
            coverage_input = self.request.data.get('coverage_limit', 0)
            currency_input = self.request.data.get('currency', 'XOF')
            
            premium_in_xof_cents = convert_to_xof(premium_input, currency_input)
            coverage_in_xof_cents = convert_to_xof(coverage_input, currency_input) if coverage_input else None
            
            serializer.save(
                premium_amount=premium_in_xof_cents,
                coverage_limit=coverage_in_xof_cents,
                currency='XOF'
            )
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category = request.query_params.get('category')
        if category:
            services = self.get_queryset().filter(category=category, is_active=True)
            from rest_framework.serializers import ModelSerializer
            
            class ServiceSerializer(ModelSerializer):
                class Meta:
                    model = InsuranceService
                    fields = '__all__'
            
            serializer = ServiceSerializer(services, many=True)
            return Response(serializer.data)
        return Response({'error': 'category required'}, status=status.HTTP_400_BAD_REQUEST)
