from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    View,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db import models as db_models, transaction
from django.http import JsonResponse
from decimal import Decimal
import json
from .models import *
from .serializers import *
from .services import WalletService
from doctor.models import DoctorData
from patient.models import PatientData, DependentProfile
from currency_converter.services import CurrencyConverterService
from .mixins import (
    PatientRequiredMixin,
    DoctorRequiredMixin,
    HospitalRequiredMixin,
    PharmacyRequiredMixin,
    InsuranceRequiredMixin,
)
from .staff_views import (
    ReceptionistDashboardView,
    ReceptionistAppointmentsView,
    ReceptionistPatientsView,
    NurseDashboardView,
    LabTechnicianDashboardView,
    HospitalPharmacistDashboardView,
    HospitalAdministratorDashboardView,
    PharmacyStaffPharmacistDashboardView,
    PharmacyCashierDashboardView,
    PharmacyInventoryClerkDashboardView,
    PharmacyDeliveryDashboardView,
    PharmacyManagerDashboardView,
)


class ParticipantViewSet(viewsets.ModelViewSet):  # ViewSet for managing participant records via REST API
    queryset = Participant.objects.all()
    serializer_class = ParticipantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Filter queryset based on role query parameter
        queryset = Participant.objects.all()
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on role"""
        role = self.request.query_params.get('role')
        if role == 'insurance_company':
            return InsuranceCompanySerializer
        return self.serializer_class
    
    @action(detail=False, methods=['get'], url_path='insurance-companies')
    def insurance_companies(self, request):
        """Get list of active insurance companies"""
        companies = Participant.objects.filter(
            role='insurance_company',
            is_active=True
        ).select_related('insurance_company_data')
        
        serializer = InsuranceCompanySerializer(companies, many=True)
        return Response({
            'count': companies.count(),
            'results': serializer.data
        })


class ParticipantProfileViewSet(viewsets.ModelViewSet):  # ViewSet for managing participant profile information via REST API
    queryset = ParticipantProfile.objects.all()
    serializer_class = ParticipantProfileSerializer
    permission_classes = [IsAuthenticated]


class WalletViewSet(viewsets.ModelViewSet):  # ViewSet for managing wallet operations and transactions
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Filter queryset to return only current user's data
        return Wallet.objects.filter(participant=self.request.user)

    @action(detail=False, methods=["get"])
    def balance(self, request):  # Get wallet balance with currency conversion support
        try:
            wallet = WalletService.get_wallet(request.user)
            user_currency = request.user.preferred_currency or wallet.currency

            balance_in_wallet_currency = wallet.balance

            if wallet.currency != user_currency:
                conversion_result = CurrencyConverterService.convert(
                    balance_in_wallet_currency, wallet.currency, user_currency
                )
                converted_balance = conversion_result['converted_amount']
            else:
                converted_balance = balance_in_wallet_currency

            return Response(
                {
                    "balance": float(converted_balance),
                    "currency": user_currency,
                    "wallet_balance": float(balance_in_wallet_currency),
                    "wallet_currency": wallet.currency,
                    "exchange_rate": float(
                        CurrencyConverterService.get_rate(wallet.currency, user_currency)
                    ),
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def update_currency(self, request):  # Update user's preferred currency preference
        try:
            new_currency = request.data.get("currency", "EUR")
            supported_currencies = [
                c["code"] for c in CurrencyConverterService.get_supported_currencies()
            ]

            if new_currency not in supported_currencies:
                return Response(
                    {"error": "Devise non supportée"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            request.user.preferred_currency = new_currency
            request.user.save()

            return Response(
                {"message": "Devise mise à jour avec succès", "currency": new_currency}
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def currencies(self, request):  # Get list of all supported currencies
        try:
            return Response(
                {
                    "currencies": CurrencyConverterService.get_supported_currencies(),
                    "current": request.user.preferred_currency or "EUR",
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def deposit(self, request):  # Deposit funds into user wallet
        try:
            amount = Decimal(request.data.get("amount", 0))
            payment_method = request.data.get("payment_method", "card")
            description = request.data.get("description", "Deposit to wallet")
            metadata = request.data.get("metadata", {})

            transaction = WalletService.deposit(
                participant=request.user,
                amount=amount,
                payment_method=payment_method,
                description=description,
                metadata=metadata,
            )

            serializer = TransactionSerializer(transaction)
            return Response(
                {"message": "Deposit successful", "transaction": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def make_payment(self, request):  # Process payment from patient to recipient
        try:
            recipient_email = request.data.get("recipient_email")
            amount = Decimal(request.data.get("amount", 0))
            description = request.data.get("description", "Payment")
            payment_method = request.data.get("payment_method", "wallet")
            metadata = request.data.get("metadata", {})

            if not recipient_email:
                return Response(
                    {"error": "recipient_email is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                recipient = Participant.objects.get(email=recipient_email)
            except Participant.DoesNotExist:
                return Response(
                    {"error": "Recipient not found"}, status=status.HTTP_404_NOT_FOUND
                )

            result = WalletService.make_payment(
                patient=request.user,
                recipient=recipient,
                amount=amount,
                description=description,
                payment_method=payment_method,
                metadata=metadata,
            )

            return Response(
                {
                    "message": "Payment successful",
                    "patient_transaction": TransactionSerializer(
                        result["patient_transaction"]
                    ).data,
                    "recipient_transaction": TransactionSerializer(
                        result["recipient_transaction"]
                    ).data,
                    "platform_fee": str(result["platform_fee"]),
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def transfer(self, request):  # Transfer funds between participant wallets
        try:
            recipient_email = request.data.get("recipient_email")
            amount = Decimal(request.data.get("amount", 0))
            description = request.data.get("description", "Fund transfer")

            if not recipient_email:
                return Response(
                    {"error": "recipient_email is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            result = WalletService.transfer_funds(
                sender=request.user,
                recipient_email=recipient_email,
                amount=amount,
                description=description,
            )

            return Response(
                {
                    "message": "Transfer successful",
                    "sender_transaction": TransactionSerializer(
                        result["sender_transaction"]
                    ).data,
                    "recipient_transaction": TransactionSerializer(
                        result["recipient_transaction"]
                    ).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def withdraw(self, request):  # Withdraw funds from wallet to bank account
        try:
            amount = Decimal(request.data.get("amount", 0))
            bank_account_info = request.data.get("bank_account_info", {})
            description = request.data.get("description", "Withdrawal to bank")

            if not bank_account_info:
                return Response(
                    {"error": "bank_account_info is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            result = WalletService.withdraw_to_bank(
                participant=request.user,
                amount=amount,
                bank_account_info=bank_account_info,
                description=description,
            )

            return Response(
                {
                    "message": "Withdrawal request submitted",
                    "withdrawal_transaction": TransactionSerializer(
                        result["withdrawal"]
                    ).data,
                    "fee_transaction": TransactionSerializer(result["fee"]).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def refund(self, request):  # Process refund for a completed payment transaction
        try:
            transaction_ref = request.data.get("transaction_ref")
            reason = request.data.get("reason", "Refund")

            if not transaction_ref:
                return Response(
                    {"error": "transaction_ref is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            result = WalletService.refund_payment(
                original_transaction_ref=transaction_ref, reason=reason
            )

            return Response(
                {
                    "message": "Refund processed successfully",
                    "patient_refund": TransactionSerializer(
                        result["patient_refund"]
                    ).data,
                    "recipient_refund": TransactionSerializer(
                        result["recipient_refund"]
                    ).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):  # ViewSet for viewing transaction history and receipts
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Filter queryset to return only current user's data
        try:
            wallet = Wallet.objects.get(participant=self.request.user)
            return Transaction.objects.filter(wallet=wallet).order_by("-created_at")
        except Wallet.DoesNotExist:
            return Transaction.objects.none()

    @action(detail=True, methods=["get"])
    def receipt(self, request, pk=None):  # Get transaction receipt data in JSON format
        try:
            transaction = self.get_object()
            receipt_data = WalletService.generate_receipt(transaction.transaction_ref)
            return Response(receipt_data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"], url_path="receipt/pdf")
    def receipt_pdf(self, request, pk=None):  # Generate and download transaction receipt as HTML/PDF
        try:
            from django.http import HttpResponse
            from django.template.loader import render_to_string
            import datetime

            transaction = self.get_object()
            receipt_data = WalletService.generate_receipt(transaction.transaction_ref)

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .header h1 {{ color: #2c3e50; margin-bottom: 5px; }}
        .header p {{ color: #7f8c8d; }}
        .receipt-box {{ border: 2px solid #3498db; border-radius: 8px; padding: 20px; }}
        .row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #ecf0f1; }}
        .label {{ font-weight: bold; color: #2c3e50; }}
        .value {{ color: #34495e; }}
        .amount {{ font-size: 24px; font-weight: bold; color: #27ae60; text-align: center; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 40px; color: #7f8c8d; font-size: 12px; }}
        .status {{ padding: 5px 10px; border-radius: 4px; display: inline-block; }}
        .status.completed {{ background-color: #d4edda; color: #155724; }}
        .status.pending {{ background-color: #fff3cd; color: #856404; }}
        .status.failed {{ background-color: #f8d7da; color: #721c24; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>BINTACURA</h1>
        <p>Reçu de Transaction</p>
    </div>
    
    <div class="receipt-box">
        <div class="row">
            <span class="label">Référence:</span>
            <span class="value">{receipt_data["transaction_ref"]}</span>
        </div>
        <div class="row">
            <span class="label">Date:</span>
            <span class="value">{receipt_data["date"].strftime("%d/%m/%Y %H:%M")}</span>
        </div>
        <div class="row">
            <span class="label">Type:</span>
            <span class="value">{receipt_data["type"]}</span>
        </div>
        <div class="row">
            <span class="label">Description:</span>
            <span class="value">{receipt_data["description"]}</span>
        </div>
        <div class="row">
            <span class="label">Méthode de paiement:</span>
            <span class="value">{receipt_data["payment_method"]}</span>
        </div>
        <div class="row">
            <span class="label">Statut:</span>
            <span class="status {receipt_data["status"].lower()}">{receipt_data["status"]}</span>
        </div>
        
        <div class="amount">
            {receipt_data["currency"]} {receipt_data["amount"]}
        </div>
        
        <div class="row">
            <span class="label">Solde avant:</span>
            <span class="value">{receipt_data["currency"]} {receipt_data["balance_before"]}</span>
        </div>
        <div class="row">
            <span class="label">Solde après:</span>
            <span class="value">{receipt_data["currency"]} {receipt_data["balance_after"]}</span>
        </div>
        
        {"<div class='row'><span class='label'>Bénéficiaire:</span><span class='value'>" + receipt_data["recipient"] + "</span></div>" if receipt_data.get("recipient") else ""}
        {"<div class='row'><span class='label'>Émetteur:</span><span class='value'>" + receipt_data["sender"] + "</span></div>" if receipt_data.get("sender") else ""}
        
        <div class="row">
            <span class="label">Titulaire du compte:</span>
            <span class="value">{receipt_data["wallet_owner"]}</span>
        </div>
    </div>
    
    <div class="footer">
        <p>BINTACURA - Plateforme de Santé Numérique</p>
        <p>Ce document constitue un reçu officiel de votre transaction.</p>
        <p>Pour toute question, contactez {settings.CONTACT_EMAIL}</p>
    </div>
</body>
</html>
"""

            response = HttpResponse(content_type="text/html")
            response["Content-Disposition"] = (
                f'attachment; filename="receipt_{transaction.transaction_ref}.html"'
            )
            response.write(html_content)
            return response

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"])
    def history(self, request):  # Get transaction history with optional filters and currency conversion
        limit = int(request.query_params.get("limit", 50))
        transaction_type = request.query_params.get("transaction_type", None)
        txn_status = request.query_params.get("status", None)

        transactions = WalletService.get_transaction_history(
            participant=request.user,
            limit=limit,
            transaction_type=transaction_type,
            status=txn_status,
        )

        user_currency = request.user.preferred_currency or "EUR"

        data = []
        for txn in transactions:
            txn_data = self.get_serializer(txn).data

            if txn.currency != user_currency:
                conversion_result = CurrencyConverterService.convert(
                    Decimal(str(txn.amount)), txn.currency, user_currency
                )
                txn_data["converted_amount"] = float(conversion_result['converted_amount'])
                txn_data["display_currency"] = user_currency
                txn_data["original_amount"] = float(txn.amount)
                txn_data["original_currency"] = txn.currency
            else:
                txn_data["converted_amount"] = float(txn.amount)
                txn_data["display_currency"] = user_currency

            data.append(txn_data)

        return Response(data)


class PatientForumView(LoginRequiredMixin, TemplateView):  # View for patient community forum page
    template_name = "patient/forum.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        return context
    
class PatientDashboardView(PatientRequiredMixin, TemplateView):  # Main dashboard view for patient users
    template_name = "dashboards/patient_dashboard.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)

        from appointments.models import Appointment
        from prescriptions.models import Prescription
        from .models import Wallet, Transaction
        from datetime import date, timedelta
        import logging

        logger = logging.getLogger(__name__)
        patient = self.request.user

        try:
            upcoming_appointments = (
                Appointment.objects.filter(
                    patient=patient,
                    status__in=["pending", "confirmed"],
                    appointment_date__gte=date.today(),
                )
                .select_related("doctor")
                .order_by("appointment_date", "appointment_time")[:3]
            )
            context["upcoming_appointments"] = upcoming_appointments
            context["upcoming_count"] = upcoming_appointments.count()
        except Exception as e:
            logger.error(f"Error fetching appointments for patient {patient.email}: {str(e)}")
            context["upcoming_appointments"] = []
            context["upcoming_count"] = 0

        try:
            recent_prescriptions = (
                Prescription.objects.filter(patient=patient)
                .select_related("doctor")
                .order_by("-issue_date")[:3]
            )
            context["recent_prescriptions"] = recent_prescriptions
            context["prescriptions_count"] = recent_prescriptions.count()
        except Exception as e:
            logger.error(f"Error fetching prescriptions for patient {patient.email}: {str(e)}")
            context["recent_prescriptions"] = []
            context["prescriptions_count"] = 0

        try:
            wallet = Wallet.objects.get(participant=patient)
            context["wallet_balance"] = wallet.balance / 100
        except Wallet.DoesNotExist:
            context["wallet_balance"] = 0
        except Exception as e:
            logger.error(f"Error fetching wallet for patient {patient.email}: {str(e)}")
            context["wallet_balance"] = 0

        return context


class DoctorDashboardView(DoctorRequiredMixin, TemplateView):  # Main dashboard view for doctor users
    template_name = "dashboards/doctor_dashboard.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from appointments.models import Appointment
        from datetime import date
        from core.models import ProviderService
        from doctor.models import DoctorAffiliation

        today = date.today()
        user = self.request.user

        context["today_appointments"] = (
            Appointment.objects.filter(
                doctor=user,
                appointment_date=today,
                status__in=["confirmed", "pending", "in_progress"],
            )
            .select_related("patient")
            .order_by("appointment_time")[:10]
        )

        context["total_today"] = context["today_appointments"].count()

        services = ProviderService.objects.filter(participant=user, is_active=True)
        context["total_services"] = services.count()
        context["active_services"] = services.filter(is_available=True).count()

        # Add affiliation information
        context["affiliations"] = DoctorAffiliation.objects.filter(
            doctor=user,
            is_active=True
        ).select_related("hospital")

        # Check if doctor is hospital staff (has locked affiliation)
        context["is_hospital_staff"] = user.affiliated_provider_id is not None
        context["can_manage_affiliations"] = not context["is_hospital_staff"]

        # Get total patients from all appointments
        context["total_patients"] = Appointment.objects.filter(doctor=user).values('patient').distinct().count()
        context["pending_appointments"] = Appointment.objects.filter(doctor=user, status='pending').count()

        return context


class HospitalDashboardView(HospitalRequiredMixin, TemplateView):  # Main dashboard view for hospital users
    template_name = "dashboards/hospital_dashboard.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.models import ProviderService, Department
        from hospital.models import Bed
        from appointments.models import Appointment
        from datetime import date

        today = date.today()
        user = self.request.user

        services = ProviderService.objects.filter(participant=user, is_active=True)
        context["total_services"] = services.count()
        context["active_services"] = services.filter(is_available=True).count()

        pending_appointments = Appointment.objects.filter(
            hospital=user, status="pending"
        ).count()
        context["pending_appointments"] = pending_appointments

        # Get bed statistics
        all_beds = Bed.objects.filter(hospital=user)
        context["total_beds"] = all_beds.count()
        context["occupied_beds"] = all_beds.filter(status="occupied").count()

        # Get department data with bed occupancy
        departments = Department.objects.filter(hospital=user, is_active=True).order_by('name')
        departments_with_stats = []
        for dept in departments:
            if dept.total_beds > 0:
                occupancy_rate = int((dept.occupied_beds / dept.total_beds) * 100)
            else:
                occupancy_rate = 0

            departments_with_stats.append({
                'name': dept.name,
                'total_beds': dept.total_beds,
                'occupied_beds': dept.occupied_beds,
                'occupancy_rate': occupancy_rate,
                'floor_number': dept.floor_number,
                'phone_number': dept.phone_number,
            })

        context["departments"] = departments_with_stats

        return context


class PharmacyDashboardView(PharmacyRequiredMixin, TemplateView):  # Main dashboard view for pharmacy users
    template_name = "dashboards/pharmacy_dashboard.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.models import ProviderService

        user = self.request.user
        services = ProviderService.objects.filter(participant=user, is_active=True)
        context["total_services"] = services.count()
        context["active_services"] = services.filter(is_available=True).count()

        return context


class InsuranceDashboardView(InsuranceRequiredMixin, TemplateView):  # Main dashboard view for insurance company users
    template_name = "dashboards/insurance_dashboard.html"
    
    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        
        from insurance.models import InsuranceClaim, InsuranceSubscription
        from django.db.models import Sum, Q
        from django.utils import timezone as tz
        
        insurance_company = self.request.user
        
        pending_claims = InsuranceClaim.objects.filter(
            insurance_package__company=insurance_company,
            status__in=['submitted', 'underReview']
        ).count()
        
        now = tz.now()
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        approved_this_month = InsuranceClaim.objects.filter(
            insurance_package__company=insurance_company,
            status__in=['approved', 'paid'],
            approval_date__gte=first_day_of_month
        ).count()
        
        active_members = InsuranceSubscription.objects.filter(
            insurance_package__company=insurance_company,
            status='active'
        ).count()
        
        total_amount_processed = InsuranceClaim.objects.filter(
            insurance_package__company=insurance_company,
            status='paid'
        ).aggregate(total=Sum('paid_amount'))['total'] or 0
        
        context['pending_claims_count'] = pending_claims
        context['approved_this_month_count'] = approved_this_month
        context['active_members_count'] = active_members
        context['total_amount_processed'] = total_amount_processed
        
        return context


class InsuranceServicesView(InsuranceRequiredMixin, TemplateView):
    """Manage insurance company services/products"""
    template_name = "insurance/services.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from core.models import ParticipantService

        services = ParticipantService.objects.filter(
            participant=self.request.user,
            is_active=True
        ).order_by("category", "name")

        context["services"] = services
        context["total_services"] = services.count()
        context["active_services"] = services.filter(is_available=True).count()

        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            from core.models import ParticipantService

            data = json.loads(request.body)
            action = data.get("action")

            if action == "create":
                ParticipantService.objects.create(
                    participant=request.user,
                    name=data.get("name"),
                    category=data.get("category", "insurance"),
                    description=data.get("description", ""),
                    price=data.get("price"),
                    currency=data.get("currency", "XOF"),
                    duration_minutes=data.get("duration_minutes"),
                    is_active=True,
                    is_available=True,
                )
                return JsonResponse(
                    {"success": True, "message": "Service ajouté avec succès"}
                )

            elif action == "update":
                service = ParticipantService.objects.get(
                    id=data.get("service_id"), participant=request.user
                )
                service.name = data.get("name", service.name)
                service.category = data.get("category", service.category)
                service.description = data.get("description", service.description)
                service.price = data.get("price", service.price)
                service.currency = data.get("currency", service.currency)
                service.duration_minutes = data.get(
                    "duration_minutes", service.duration_minutes
                )
                service.is_available = data.get("is_available", service.is_available)
                service.save()

                return JsonResponse(
                    {"success": True, "message": "Service modifié avec succès"}
                )

            elif action == "delete":
                service = ParticipantService.objects.get(
                    id=data.get("service_id"), participant=request.user
                )
                service.is_active = False
                service.save()

                return JsonResponse(
                    {"success": True, "message": "Service désactivé avec succès"}
                )

            return JsonResponse(
                {"success": False, "message": "Action invalide"}, status=400
            )

        except ParticipantService.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Service introuvable"}, status=404
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


class MainDashboardView(LoginRequiredMixin, TemplateView):  # Generic main dashboard view with role-based routing
    template_name = "dashboards/main_dashboard.html"
    login_url = "/auth/login/"


class PatientProfileView(PatientRequiredMixin, TemplateView):  # View and edit patient profile information
    template_name = "patient/profile.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        # Get or create patient_data
        from patient.models import PatientData

        patient_data, created = PatientData.objects.get_or_create(
            participant=self.request.user
        )
        context["patient_data"] = patient_data

        # Parse full_name into first and last name for the form
        full_name = self.request.user.full_name or ""
        name_parts = full_name.split(maxsplit=1)
        context["first_name"] = name_parts[0] if name_parts else ""
        context["last_name"] = name_parts[1] if len(name_parts) > 1 else ""

        return context

    def post(self, request, *args, **kwargs):
        from patient.models import PatientData
        from datetime import datetime
        import boto3
        from django.conf import settings
        import uuid

        try:
            patient_data, created = PatientData.objects.get_or_create(
                participant=request.user
            )

            participant = request.user
            participant.full_name = f"{request.POST.get('first_name', '')} {request.POST.get('last_name', '')}".strip()
            participant.email = request.POST.get("email", participant.email)
            participant.phone_number = request.POST.get("phone_number", "")
            
            date_of_birth = request.POST.get("date_of_birth", "")
            if date_of_birth:
                participant.date_of_birth = date_of_birth
            
            participant.gender = request.POST.get("gender", "")
            
            if request.FILES.get('profile_picture'):
                profile_picture = request.FILES['profile_picture']

                # ISSUE-PAT-003: Increased file size limit from 2MB to 5MB
                # Use validators for consistency
                from .validators import validate_profile_picture_size, validate_profile_picture_format
                from django.core.exceptions import ValidationError as DjangoValidationError

                try:
                    validate_profile_picture_size(profile_picture)
                    validate_profile_picture_format(profile_picture)
                except DjangoValidationError as e:
                    return JsonResponse(
                        {"status": "error", "message": str(e.message)},
                        status=400
                    )

                try:
                    s3_client = boto3.client(
                        's3',
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        region_name=settings.AWS_S3_REGION_NAME
                    )

                    file_extension = profile_picture.name.split('.')[-1].lower()
                    file_name = f"profile_pictures/{participant.uid}_{uuid.uuid4()}.{file_extension}"

                    s3_client.upload_fileobj(
                        profile_picture,
                        settings.AWS_STORAGE_BUCKET_NAME,
                        file_name,
                        ExtraArgs={'ContentType': profile_picture.content_type, 'ACL': 'public-read'}
                    )

                    participant.profile_picture_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{file_name}"
                except Exception as e:
                    return JsonResponse(
                        {"status": "error", "message": f"Erreur lors du téléchargement de l'image: {str(e)}"},
                        status=400
                    )
            
            participant.save()

            patient_data.blood_type = request.POST.get("blood_type", "")
            patient_data.profession = request.POST.get("profession", "")
            patient_data.marital_status = request.POST.get("marital_status", "")
            
            number_of_children = request.POST.get("number_of_children", "0")
            patient_data.number_of_children = int(number_of_children) if number_of_children else 0

            allergies_text = request.POST.get("allergies", "").strip()
            if allergies_text:
                patient_data.allergies = [
                    a.strip() for a in allergies_text.split("\n") if a.strip()
                ]
            else:
                patient_data.allergies = []

            conditions_text = request.POST.get("medical_conditions", "").strip()
            if conditions_text:
                patient_data.chronic_conditions = [
                    c.strip() for c in conditions_text.split("\n") if c.strip()
                ]
            else:
                patient_data.chronic_conditions = []

            patient_data.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Profil mis à jour avec succès!",
                    "profile_picture_url": participant.profile_picture_url,
                    "initials": participant.get_initials()
                }
            )

        except Exception as e:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Erreur lors de la mise à jour: {str(e)}",
                },
                status=400,
            )


class PatientBeneficiariesView(PatientRequiredMixin, TemplateView):  # View patient beneficiaries and dependent profiles
    template_name = "patient/beneficiaries.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from patient.models import DependentProfile

        beneficiaries = DependentProfile.objects.filter(
            patient=self.request.user, is_active=True
        ).order_by("-created_at")

        context["beneficiaries"] = beneficiaries
        context["beneficiaries_count"] = beneficiaries.count()
        return context


class PatientSettingsView(PatientRequiredMixin, TemplateView):  # Patient account settings and preferences view
    template_name = "shared/settings.html"
    
    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.preferences_utils import get_or_create_preferences
        context['preferences'] = get_or_create_preferences(self.request.user)
        return context


class PatientPrivacyView(PatientRequiredMixin, TemplateView):  # Patient privacy settings and data management view
    template_name = "patient/privacy.html"


class DoctorPatientsView(DoctorRequiredMixin, TemplateView):  # View doctor's patient list
    template_name = "doctor/patients.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from appointments.models import Appointment

        appointments = (
            Appointment.objects.filter(doctor=self.request.user)
            .select_related("patient")
            .order_by("patient")
        )

        # Get unique patients (MySQL doesn't support DISTINCT ON)
        seen_patients = set()
        unique_patients = []
        for apt in appointments:
            if apt.patient and apt.patient.uid not in seen_patients:
                seen_patients.add(apt.patient.uid)
                unique_patients.append(apt.patient)

        context["patients"] = unique_patients
        return context


class DoctorAppointmentsView(DoctorRequiredMixin, TemplateView):  # View doctor's appointment schedule
    template_name = "doctor/appointments.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from appointments.models import Appointment, AppointmentQueue
        from datetime import date

        today = date.today()
        user = self.request.user

        context["pending_appointments"] = (
            Appointment.objects.filter(doctor=user, status="pending")
            .select_related("patient")
            .order_by("appointment_date", "appointment_time")
        )

        context["confirmed_appointments"] = (
            Appointment.objects.filter(doctor=user, status="confirmed")
            .select_related("patient")
            .order_by("appointment_date", "appointment_time")
        )

        context["today_appointments"] = (
            Appointment.objects.filter(
                doctor=user,
                appointment_date=today,
                status__in=["confirmed", "in_progress"],
            )
            .select_related("patient")
            .order_by("appointment_time")
        )

        context["queue_entries"] = (
            AppointmentQueue.objects.filter(provider=user, status="waiting")
            .select_related("appointment__patient")
            .order_by("queue_number")
        )

        return context


class DoctorConsultationsView(DoctorRequiredMixin, TemplateView):  # View doctor's consultation history
    template_name = "doctor/consultations.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from health_records.models import TelemedicineSession

        context["scheduled_sessions"] = (
            TelemedicineSession.objects.filter(
                doctor=self.request.user, status="scheduled"
            )
            .select_related("patient")
            .order_by("scheduled_start_time")
        )

        context["in_progress_sessions"] = (
            TelemedicineSession.objects.filter(
                doctor=self.request.user, status="in_progress"
            )
            .select_related("patient")
            .order_by("scheduled_start_time")
        )

        context["completed_sessions"] = (
            TelemedicineSession.objects.filter(
                doctor=self.request.user, status="completed"
            )
            .select_related("patient")
            .order_by("-scheduled_start_time")[:10]
        )

        return context


class DoctorPrescriptionsView(DoctorRequiredMixin, TemplateView):  # View doctor's prescription records
    template_name = "doctor/prescriptions.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from prescriptions.models import Prescription
        from doctor.models import DoctorData

        doctor = self.request.user
        doctor_data = DoctorData.objects.filter(participant=doctor).first()

        prescriptions = (
            Prescription.objects.filter(doctor=doctor)
            .select_related("patient", "doctor")
            .prefetch_related("items", "items__medication")
            .order_by("-issue_date")
        )

        active_prescriptions = prescriptions.filter(status="active")
        pending_prescriptions = prescriptions.filter(status="pendingRenewal")

        context["doctor_data"] = doctor_data
        context["prescriptions"] = prescriptions[:20]
        context["active_count"] = active_prescriptions.count()
        context["pending_count"] = pending_prescriptions.count()
        context["total_count"] = prescriptions.count()

        return context


class DoctorScheduleView(DoctorRequiredMixin, TemplateView):
    template_name = "doctor/schedule.html"


class DoctorCalendarView(DoctorRequiredMixin, TemplateView):
    template_name = "doctor/calendar.html"


class DoctorProfileView(DoctorRequiredMixin, TemplateView):
    template_name = "doctor/profile.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from doctor.models import DoctorData, DoctorAffiliation
        from core.models import UserProfile

        user = self.request.user
        context["user"] = user

        try:
            doctor_data = DoctorData.objects.get(participant=user)
            context["doctor_data"] = doctor_data
        except DoctorData.DoesNotExist:
            context["doctor_data"] = None

        try:
            user_profile = UserProfile.objects.get(participant=user)
            context["user_profile"] = user_profile
        except UserProfile.DoesNotExist:
            context["user_profile"] = None

        # Add affiliation information
        context["affiliations"] = DoctorAffiliation.objects.filter(
            doctor=user,
            is_active=True
        ).select_related("hospital")

        # Check if doctor is hospital staff (has locked affiliation)
        context["is_hospital_staff"] = user.affiliated_provider_id is not None
        context["can_manage_affiliations"] = not context["is_hospital_staff"]

        return context


class DoctorSettingsView(DoctorRequiredMixin, TemplateView):  # Doctor account settings and preferences
    template_name = "shared/settings.html"
    
    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.preferences_utils import get_or_create_preferences
        context['preferences'] = get_or_create_preferences(self.request.user)
        return context


class DoctorLaboratoryView(DoctorRequiredMixin, TemplateView):  # Doctor laboratory requests and results
    template_name = "doctor/laboratory.html"


class DoctorReferralsView(DoctorRequiredMixin, TemplateView):  # Doctor patient referrals management
    template_name = "doctor/referrals.html"


class DoctorCertificatesView(DoctorRequiredMixin, TemplateView):  # Doctor medical certificates management
    template_name = "doctor/certificates.html"


class DoctorNewPrescriptionView(DoctorRequiredMixin, TemplateView):  # Create new prescription form view
    template_name = "doctor/new_prescription.html"


class DoctorMedicalRecordView(DoctorRequiredMixin, TemplateView):  # View patient medical record details
    template_name = "doctor/medical_record.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from health_records.models import HealthRecord
        from patient.models import PatientData

        patient_id = self.kwargs.get("patient_id")

        if patient_id:
            try:
                patient = Participant.objects.get(uid=patient_id, role="patient")
                context["patient"] = patient

                try:
                    patient_data = PatientData.objects.get(participant=patient)
                    context["patient_data"] = patient_data
                except PatientData.DoesNotExist:
                    context["patient_data"] = None

                context["medical_records"] = (
                    HealthRecord.objects.filter(assigned_to=patient)
                    .select_related("created_by")
                    .order_by("-date_of_record")[:10]
                )

            except Participant.DoesNotExist:
                context["patient"] = None
                context["error"] = "Patient not found"

        return context


class DoctorLabRequestView(DoctorRequiredMixin, TemplateView):  # Create new laboratory request
    template_name = "doctor/lab_request.html"


class DoctorReferralView(DoctorRequiredMixin, TemplateView):  # Create new patient referral
    template_name = "doctor/referral.html"


class DoctorServicesView(DoctorRequiredMixin, TemplateView):  # Manage doctor services and pricing
    template_name = "doctor/services.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.models import ParticipantService

        services = ParticipantService.objects.filter(
            participant=self.request.user, is_active=True
        ).order_by("-created_at")

        context["services"] = services
        context["total_services"] = services.count()
        context["active_services"] = services.filter(is_available=True).count()

        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):  # Handle form submission for data updates
        try:
            from core.models import ParticipantService
            from decimal import Decimal

            data = json.loads(request.body)
            action = data.get("action")

            if action == "create":
                # Price comes in major units (XOF), store as Decimal
                price = Decimal(str(data.get("price", 0)))
                
                ParticipantService.objects.create(
                    participant=request.user,
                    name=data.get("name"),
                    category=data.get("category"),
                    description=data.get("description", ""),
                    price=price,
                    currency=data.get("currency", "XOF"),
                    duration_minutes=data.get("duration_minutes"),
                    is_active=True,
                    is_available=True,
                )
                return JsonResponse(
                    {"success": True, "message": "Service ajouté avec succès"}
                )

            elif action == "update":
                service = ParticipantService.objects.get(
                    id=data.get("service_id"), participant=request.user
                )
                service.name = data.get("name", service.name)
                service.category = data.get("category", service.category)
                service.description = data.get("description", service.description)
                
                if "price" in data:
                    service.price = Decimal(str(data.get("price")))
                service.currency = data.get("currency", service.currency)
                service.duration_minutes = data.get(
                    "duration_minutes", service.duration_minutes
                )
                service.is_available = data.get("is_available", service.is_available)
                service.save()

                return JsonResponse(
                    {"success": True, "message": "Service modifié avec succès"}
                )

            elif action == "delete":
                service = ParticipantService.objects.get(
                    id=data.get("service_id"), participant=request.user
                )
                service.is_active = False
                service.save()

                return JsonResponse(
                    {"success": True, "message": "Service désactivé avec succès"}
                )

            return JsonResponse(
                {"success": False, "message": "Action invalide"}, status=400
            )

        except DoctorService.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Service introuvable"}, status=404
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


class DoctorBonusesView(DoctorRequiredMixin, TemplateView):  # View doctor bonus and incentive information
    template_name = "doctor/bonuses.html"


class HospitalPatientsView(HospitalRequiredMixin, TemplateView):  # View hospital patient list
    template_name = "hospital/patients.html"


class HospitalAdmissionsView(HospitalRequiredMixin, TemplateView):  # View hospital patient admissions
    template_name = "hospital/admissions.html"


class HospitalDepartmentsView(HospitalRequiredMixin, TemplateView):  # Manage hospital departments
    template_name = "hospital/departments.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        hospital_id = self.request.user.uid

        from core.models import Department

        departments = Department.objects.filter(
            hospital_id=hospital_id, is_active=True
        ).order_by("name")

        context["departments"] = departments
        context["total_departments"] = departments.count()
        context["total_beds"] = sum(d.total_beds for d in departments)
        context["occupied_beds"] = sum(d.occupied_beds for d in departments)
        context["total_staff"] = sum(d.total_staff for d in departments)

        return context

    def post(self, request, *args, **kwargs):  # Handle form submission for data updates
        try:
            from core.models import Department

            data = json.loads(request.body)
            action = data.get("action")
            hospital_id = request.user.uid

            if action == "create":
                name = data.get("name")
                description = data.get("description", "")
                total_beds = int(data.get("total_beds", 0))
                occupied_beds = int(data.get("occupied_beds", 0))
                total_staff = int(data.get("total_staff", 0))
                phone_number = data.get("phone_number", "")
                floor_number = data.get("floor_number", "")

                if not name:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Le nom du département est requis",
                        },
                        status=400,
                    )

                if Department.objects.filter(
                    hospital_id=hospital_id, name=name
                ).exists():
                    return JsonResponse(
                        {"success": False, "message": "Ce département existe déjà"},
                        status=400,
                    )

                Department.objects.create(
                    hospital_id=hospital_id,
                    name=name,
                    description=description,
                    total_beds=total_beds,
                    occupied_beds=occupied_beds,
                    total_staff=total_staff,
                    phone_number=phone_number,
                    floor_number=floor_number,
                    is_active=True,
                )

                return JsonResponse(
                    {"success": True, "message": "Département ajouté avec succès"}
                )

            elif action == "update":
                dept_id = data.get("dept_id")
                dept = Department.objects.get(id=dept_id, hospital_id=hospital_id)

                dept.name = data.get("name", dept.name)
                dept.description = data.get("description", dept.description)
                dept.total_beds = int(data.get("total_beds", dept.total_beds))
                dept.occupied_beds = int(data.get("occupied_beds", dept.occupied_beds))
                dept.total_staff = int(data.get("total_staff", dept.total_staff))
                dept.phone_number = data.get("phone_number", dept.phone_number)
                dept.floor_number = data.get("floor_number", dept.floor_number)
                dept.save()

                return JsonResponse(
                    {"success": True, "message": "Département mis à jour avec succès"}
                )

            elif action == "delete":
                dept_id = data.get("dept_id")
                dept = Department.objects.get(id=dept_id, hospital_id=hospital_id)
                dept.is_active = False
                dept.save()

                return JsonResponse(
                    {"success": True, "message": "Département désactivé avec succès"}
                )

            return JsonResponse(
                {"success": False, "message": "Action invalide"}, status=400
            )

        except Department.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Département introuvable"}, status=404
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


class HospitalStaffView(HospitalRequiredMixin, TemplateView):  # Manage hospital staff members
    template_name = "hospital/staff.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        hospital_id = self.request.user.uid

        staff_members = (
            Participant.objects.filter(
                affiliated_provider_id=hospital_id, role__in=["doctor", "hospital"]
            )
            .exclude(uid=hospital_id)
            .order_by("-created_at")
        )

        context["staff_members"] = staff_members
        context["staff_count"] = staff_members.count()
        context["doctors_count"] = staff_members.filter(staff_role="doctor").count()
        context["nurses_count"] = staff_members.filter(staff_role="nurse").count()
        context["admin_count"] = staff_members.filter(
            staff_role="administrator"
        ).count()

        return context

    def post(self, request, *args, **kwargs):  # Handle form submission for data updates
        try:
            data = json.loads(request.body)
            action = data.get("action")
            hospital_id = request.user.uid

            if action == "create":
                full_name = data.get("full_name")
                email = data.get("email")
                staff_role = data.get("staff_role")
                department = data.get("department")
                phone_number = data.get("phone_number", "")
                gender = data.get("gender", "")
                address = data.get("address", "")
                privileges = data.get("privileges", "")

                if not all([full_name, email, staff_role]):
                    return JsonResponse(
                        {"success": False, "message": "Champs obligatoires manquants"},
                        status=400,
                    )

                if Participant.objects.filter(email=email).exists():
                    return JsonResponse(
                        {"success": False, "message": "Cet email existe déjà"},
                        status=400,
                    )

                import random
                import string

                temp_password = "".join(
                    random.choices(string.ascii_letters + string.digits, k=12)
                )

                staff = Participant.objects.create(
                    email=email,
                    full_name=full_name,
                    role="hospital",
                    staff_role=staff_role,
                    department=department,
                    phone_number=phone_number,
                    gender=gender,
                    address=address,
                    affiliated_provider_id=hospital_id,
                    employee_id=f"EMP-{staff_role[:3].upper()}-{random.randint(100000, 999999)}",
                    is_active=True,
                )
                staff.set_password(temp_password)
                staff.save()

                return JsonResponse(
                    {
                        "success": True,
                        "message": f"Personnel ajouté avec succès. Mot de passe temporaire: {temp_password}",
                    }
                )

            elif action == "update":
                staff_id = data.get("staff_id")
                staff = Participant.objects.get(
                    uid=staff_id, affiliated_provider_id=hospital_id
                )

                staff.full_name = data.get("full_name", staff.full_name)
                staff.email = data.get("email", staff.email)
                staff.staff_role = data.get("staff_role", staff.staff_role)
                staff.department = data.get("department", staff.department)
                staff.phone_number = data.get("phone_number", staff.phone_number)
                staff.gender = data.get("gender", staff.gender)
                staff.address = data.get("address", staff.address)
                staff.is_active = data.get("is_active", staff.is_active)

                staff.save()

                return JsonResponse(
                    {"success": True, "message": "Personnel mis à jour avec succès"}
                )

            elif action == "delete":
                staff_id = data.get("staff_id")
                staff = Participant.objects.get(
                    uid=staff_id, affiliated_provider_id=hospital_id
                )
                staff.is_active = False
                staff.save()

                return JsonResponse(
                    {"success": True, "message": "Personnel désactivé avec succès"}
                )

            return JsonResponse(
                {"success": False, "message": "Action invalide"}, status=400
            )

        except Participant.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Personnel introuvable"}, status=404
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


class HospitalBedsView(HospitalRequiredMixin, TemplateView):  # Manage hospital bed availability
    template_name = "hospital/beds.html"


class HospitalReportsView(HospitalRequiredMixin, TemplateView):  # View hospital reports and statistics
    template_name = "hospital/reports.html"


class HospitalProfileView(HospitalRequiredMixin, TemplateView):  # View and edit hospital profile information
    template_name = "hospital/profile.html"
    
    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.models import LegalRepresentative
        try:
            context['legal_representative'] = LegalRepresentative.objects.get(participant=self.request.user)
        except LegalRepresentative.DoesNotExist:
            context['legal_representative'] = None
        return context


class HospitalSettingsView(HospitalRequiredMixin, TemplateView):  # Hospital account settings and preferences
    template_name = "shared/settings.html"
    
    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.preferences_utils import get_or_create_preferences
        context['preferences'] = get_or_create_preferences(self.request.user)
        return context


class HospitalEquipmentView(HospitalRequiredMixin, TemplateView):  # Manage hospital equipment inventory
    template_name = "hospital/equipment.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.models import MedicalEquipment

        hospital_id = self.request.user.uid
        equipment_list = MedicalEquipment.objects.filter(
            hospital=self.request.user, is_active=True
        ).select_related("assigned_to_patient")

        context["equipment_list"] = equipment_list
        context["total_equipment"] = equipment_list.count()
        context["available_count"] = equipment_list.filter(status="available").count()
        context["in_use_count"] = equipment_list.filter(status="in_use").count()
        context["maintenance_count"] = equipment_list.filter(
            status="maintenance"
        ).count()
        context["out_of_order_count"] = equipment_list.filter(
            status="out_of_order"
        ).count()

        return context

    def post(self, request, *args, **kwargs):  # Handle form submission for data updates
        from core.models import MedicalEquipment
        from django.http import JsonResponse
        import json

        try:
            data = json.loads(request.body)
            action = data.get("action")

            if action == "create":
                equipment = MedicalEquipment.objects.create(
                    name=data.get("name"),
                    category=data.get("category", "other"),
                    manufacturer=data.get("manufacturer", ""),
                    model_number=data.get("model_number", ""),
                    serial_number=data.get("serial_number", ""),
                    hospital=request.user,
                    location=data.get("location", ""),
                    department=data.get("department", ""),
                    status=data.get("status", "available"),
                    notes=data.get("notes", ""),
                )
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Équipement ajouté avec succès",
                        "equipment_id": equipment.equipment_id,
                    }
                )

            elif action == "update":
                equipment = MedicalEquipment.objects.get(
                    id=data.get("equipment_id"), hospital=request.user
                )

                equipment.name = data.get("name", equipment.name)
                equipment.category = data.get("category", equipment.category)
                equipment.manufacturer = data.get(
                    "manufacturer", equipment.manufacturer
                )
                equipment.model_number = data.get(
                    "model_number", equipment.model_number
                )
                equipment.serial_number = data.get(
                    "serial_number", equipment.serial_number
                )
                equipment.location = data.get("location", equipment.location)
                equipment.department = data.get("department", equipment.department)
                equipment.status = data.get("status", equipment.status)
                equipment.notes = data.get("notes", equipment.notes)
                equipment.problem_description = data.get(
                    "problem_description", equipment.problem_description
                )

                if "last_maintenance_date" in data:
                    equipment.last_maintenance_date = data.get("last_maintenance_date")
                if "next_maintenance_date" in data:
                    equipment.next_maintenance_date = data.get("next_maintenance_date")

                equipment.save()

                return JsonResponse(
                    {"success": True, "message": "Équipement modifié avec succès"}
                )

            elif action == "delete":
                equipment = MedicalEquipment.objects.get(
                    id=data.get("equipment_id"), hospital=request.user
                )
                equipment.is_active = False
                equipment.save()

                return JsonResponse(
                    {"success": True, "message": "Équipement supprimé avec succès"}
                )

            else:
                return JsonResponse(
                    {"success": False, "message": "Action non reconnue"}, status=400
                )

        except MedicalEquipment.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Équipement non trouvé"}, status=404
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


class HospitalServicesView(HospitalRequiredMixin, TemplateView):  # Manage hospital services and pricing
    template_name = "hospital/services.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.models import ParticipantService

        services = ParticipantService.objects.filter(participant=self.request.user).order_by(
            "category", "name"
        )

        context["services"] = services
        context["total_services"] = services.count()
        context["active_services"] = services.filter(is_active=True).count()

        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):  # Handle form submission for data updates
        from core.models import ParticipantService
        from decimal import Decimal

        try:
            data = json.loads(request.body)
            action = data.get("action")

            if action == "create":
                service = ParticipantService.objects.create(
                    participant=request.user,
                    name=data.get("name"),
                    category=data.get("category"),
                    description=data.get("description", ""),
                    price=Decimal(str(data.get("price"))),
                    currency=data.get("currency", "XOF"),
                    duration_minutes=data.get("duration_minutes"),
                    is_active=True,
                    is_available=True,
                )
                return JsonResponse(
                    {"success": True, "message": "Service ajouté avec succès"}
                )

            elif action == "update":
                service = ParticipantService.objects.get(
                    id=data.get("service_id"), participant=request.user
                )
                service.name = data.get("name", service.name)
                service.category = data.get("category", service.category)
                service.description = data.get("description", service.description)
                if "price" in data:
                    service.price = Decimal(str(data.get("price")))
                service.currency = data.get("currency", service.currency)
                service.duration_minutes = data.get(
                    "duration_minutes", service.duration_minutes
                )
                service.is_available = data.get("is_available", service.is_available)
                service.save()

                return JsonResponse(
                    {"success": True, "message": "Service modifié avec succès"}
                )

            elif action == "delete":
                service = ParticipantService.objects.get(
                    id=data.get("service_id"), participant=request.user
                )
                service.is_active = False
                service.save()

                return JsonResponse(
                    {"success": True, "message": "Service désactivé avec succès"}
                )

            return JsonResponse(
                {"success": False, "message": "Action invalide"}, status=400
            )

        except ProviderService.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Service introuvable"}, status=404
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


class HospitalAppointmentsView(HospitalRequiredMixin, TemplateView):  # View hospital appointment schedule
    template_name = "hospital/appointments.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from appointments.models import Appointment
        from datetime import date

        today = date.today()
        hospital_id = self.request.user.uid

        pending_appointments = (
            Appointment.objects.filter(facility=self.request.user, status="pending")
            .select_related("patient")
            .order_by("appointment_date", "appointment_time")
        )

        today_appointments = (
            Appointment.objects.filter(
                facility=self.request.user,
                appointment_date=today,
                status__in=["confirmed", "in_progress"],
            )
            .select_related("patient", "doctor")
            .order_by("appointment_time")
        )

        upcoming_appointments = (
            Appointment.objects.filter(
                facility=self.request.user,
                appointment_date__gt=today,
                status__in=["pending", "confirmed"],
            )
            .select_related("patient", "doctor")
            .order_by("appointment_date", "appointment_time")
        )

        completed_appointments = (
            Appointment.objects.filter(facility=self.request.user, status="completed")
            .select_related("patient", "doctor")
            .order_by("-appointment_date", "-appointment_time")[:20]
        )

        available_staff = Participant.objects.filter(
            affiliated_provider_id=hospital_id,
            staff_role__in=["doctor", "nurse"],
            is_active=True,
        ).order_by("full_name")

        context["pending_appointments"] = pending_appointments
        context["today_appointments"] = today_appointments
        context["upcoming_appointments"] = upcoming_appointments
        context["completed_appointments"] = completed_appointments
        context["available_staff"] = available_staff
        context["pending_count"] = pending_appointments.count()
        context["today_count"] = today_appointments.count()
        context["upcoming_count"] = upcoming_appointments.count()

        return context

    def post(self, request, *args, **kwargs):  # Handle form submission for data updates
        from appointments.models import Appointment
        from communication.services import NotificationService

        try:
            data = json.loads(request.body)
            action = data.get("action")

            if action == "assign":
                appointment = Appointment.objects.get(
                    id=data.get("appointment_id"), facility=request.user
                )
                staff_id = data.get("staff_id")

                if staff_id:
                    staff_member = Participant.objects.get(
                        uid=staff_id, affiliated_provider_id=request.user.uid
                    )
                    appointment.doctor = staff_member
                    appointment.status = "confirmed"
                    appointment.save()

                    NotificationService.create_notification(
                        {
                            "recipient": staff_member,
                            "notification_type": "appointment",
                            "title": "Nouveau rendez-vous assigné",
                            "message": f"Un rendez-vous avec {appointment.patient.full_name} a été assigné pour le {appointment.appointment_date}",
                            "action_url": f"/doctor/appointments/",
                        }
                    )

                    NotificationService.create_notification(
                        {
                            "recipient": appointment.patient,
                            "notification_type": "appointment",
                            "title": "Rendez-vous confirmé",
                            "message": f"Votre rendez-vous a été confirmé avec {staff_member.full_name}",
                            "action_url": f"/patient/my-appointments/",
                        }
                    )

                    return JsonResponse(
                        {"success": True, "message": "Rendez-vous assigné avec succès"}
                    )

            elif action == "cancel":
                appointment = Appointment.objects.get(
                    id=data.get("appointment_id"), facility=request.user
                )
                appointment.status = "cancelled"
                appointment.cancellation_reason = data.get("reason", "")
                appointment.cancelled_at = timezone.now()
                appointment.save()

                NotificationService.create_notification(
                    {
                        "recipient": appointment.patient,
                        "notification_type": "appointment",
                        "title": "Rendez-vous annulé",
                        "message": f"Votre rendez-vous du {appointment.appointment_date} a été annulé",
                        "action_url": f"/patient/my-appointments/",
                    }
                )

                return JsonResponse(
                    {"success": True, "message": "Rendez-vous annulé avec succès"}
                )

            return JsonResponse(
                {"success": False, "message": "Action invalide"}, status=400
            )

        except Appointment.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Rendez-vous introuvable"}, status=404
            )
        except Participant.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Personnel introuvable"}, status=404
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


class PharmacyPrescriptionsView(PharmacyRequiredMixin, TemplateView):  # View pharmacy prescriptions to fill
    template_name = "pharmacy/prescriptions.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from prescriptions.models import Prescription

        prescriptions_base = Prescription.objects.filter(
            preferred_pharmacy_id=self.request.user.uid
        ).select_related('patient', 'doctor').order_by('-issue_date')

        context['prescriptions'] = prescriptions_base[:50]
        context['pending_count'] = prescriptions_base.filter(status='active').count()
        context['processing_count'] = prescriptions_base.filter(status='ordered').count()
        context['ready_count'] = prescriptions_base.filter(status='verified').count()
        context['delivered_count'] = prescriptions_base.filter(status='fulfilled').count()

        return context


class PharmacyPatientsView(PharmacyRequiredMixin, TemplateView):  # View pharmacy patient list
    template_name = "pharmacy/patients.html"


class PharmacyInventoryView(PharmacyRequiredMixin, TemplateView):  # Manage pharmacy medication inventory
    template_name = "pharmacy/inventory.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from pharmacy.models import PharmacyInventory
        from prescriptions.models import Medication
        from django.db.models import Q, Sum

        inventory = PharmacyInventory.objects.filter(
            pharmacy_id=self.request.user.uid
        ).select_related('medication').order_by('medication__name')

        context['inventory'] = inventory
        context['total_items'] = inventory.count()
        context['low_stock_items'] = inventory.filter(
            quantity_in_stock__lte=models.F('reorder_level')
        ).count()
        context['out_of_stock_items'] = inventory.filter(quantity_in_stock=0).count()
        context['total_value'] = inventory.aggregate(
            total=Sum(models.F('quantity_in_stock') * models.F('unit_price'))
        )['total'] or 0

        context['all_medications'] = Medication.objects.all().order_by('name')

        return context

    def post(self, request, *args, **kwargs):  # Handle form submission for data updates
        from pharmacy.models import PharmacyInventory
        from prescriptions.models import Medication
        from django.http import JsonResponse
        from datetime import datetime
        import json

        try:
            data = json.loads(request.body)
            action = data.get('action')

            if action == 'add_medication':
                medication_data = {
                    'name': data.get('name'),
                    'generic_name': data.get('generic_name', ''),
                    'brand_name': data.get('brand_name', ''),
                    'category': data.get('category', ''),
                    'description': data.get('description', ''),
                    'manufacturer': data.get('manufacturer', ''),
                    'is_controlled_substance': data.get('is_controlled_substance', False),
                    'requires_prescription': data.get('requires_prescription', True),
                    'side_effects': data.get('side_effects', ''),
                    'contraindications': data.get('contraindications', ''),
                    'dosage_forms': data.get('dosage_forms', []),
                    'strengths': data.get('strengths', [])
                }

                medication = Medication.objects.create(**medication_data)

                inventory_data = {
                    'pharmacy_id': request.user.uid,
                    'medication': medication,
                    'batch_number': data.get('batch_number', ''),
                    'quantity_in_stock': int(data.get('quantity_in_stock', 0)),
                    'unit_price': int(data.get('unit_price', 0)),
                    'selling_price': int(data.get('selling_price', 0)),
                    'manufacturer': data.get('manufacturer', ''),
                    'manufacturing_date': datetime.strptime(data.get('manufacturing_date'), '%Y-%m-%d').date() if data.get('manufacturing_date') else None,
                    'expiry_date': datetime.strptime(data.get('expiry_date'), '%Y-%m-%d').date(),
                    'reorder_level': int(data.get('reorder_level', 10)),
                    'storage_location': data.get('storage_location', ''),
                    'requires_refrigeration': data.get('requires_refrigeration', False),
                    'is_publicly_available': data.get('is_publicly_available', True)
                }

                inventory = PharmacyInventory.objects.create(**inventory_data)

                return JsonResponse({
                    'success': True,
                    'message': 'Medication added successfully',
                    'medication_id': str(medication.id),
                    'inventory_id': str(inventory.id)
                })

            elif action == 'add_to_inventory':
                medication_id = data.get('medication_id')
                medication = Medication.objects.get(id=medication_id)

                inventory_data = {
                    'pharmacy_id': request.user.uid,
                    'medication': medication,
                    'batch_number': data.get('batch_number', ''),
                    'quantity_in_stock': int(data.get('quantity_in_stock', 0)),
                    'unit_price': int(data.get('unit_price', 0)),
                    'selling_price': int(data.get('selling_price', 0)),
                    'manufacturer': data.get('manufacturer', ''),
                    'manufacturing_date': datetime.strptime(data.get('manufacturing_date'), '%Y-%m-%d').date() if data.get('manufacturing_date') else None,
                    'expiry_date': datetime.strptime(data.get('expiry_date'), '%Y-%m-%d').date(),
                    'reorder_level': int(data.get('reorder_level', 10)),
                    'storage_location': data.get('storage_location', ''),
                    'requires_refrigeration': data.get('requires_refrigeration', False),
                    'is_publicly_available': data.get('is_publicly_available', True)
                }

                inventory = PharmacyInventory.objects.create(**inventory_data)

                return JsonResponse({
                    'success': True,
                    'message': 'Medication added to inventory successfully',
                    'inventory_id': str(inventory.id)
                })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)


class PharmacyOrdersView(PharmacyRequiredMixin, TemplateView):  # View pharmacy supplier orders
    template_name = "pharmacy/orders.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from pharmacy.models import PharmacyOrder

        orders_base = PharmacyOrder.objects.filter(
            pharmacy_id=self.request.user.uid
        ).select_related('patient').prefetch_related('items').order_by('-order_date')

        context['orders'] = orders_base[:50]
        context['pending_orders'] = orders_base.filter(status='pending').count()
        context['processing_orders'] = orders_base.filter(status='processing').count()
        context['ready_orders'] = orders_base.filter(status='ready').count()
        context['delivered_orders'] = orders_base.filter(status='delivered').count()

        return context


class PharmacySuppliersView(PharmacyRequiredMixin, TemplateView):  # Manage pharmacy suppliers
    template_name = "pharmacy/suppliers.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from pharmacy.models import PharmacySupplier

        suppliers = PharmacySupplier.objects.filter(
            pharmacy_id=self.request.user.uid
        ).order_by('name')

        context['suppliers'] = suppliers
        context['active_suppliers'] = suppliers.filter(is_active=True).count()
        context['total_suppliers'] = suppliers.count()

        return context


class PharmacySalesView(PharmacyRequiredMixin, TemplateView):  # View pharmacy sales records
    template_name = "pharmacy/sales.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from pharmacy.models import PharmacySale
        from django.db.models import Sum, Count
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        sales_base = PharmacySale.objects.filter(
            pharmacy_id=self.request.user.uid
        ).select_related('patient').prefetch_related('items').order_by('-sale_date')

        context['sales'] = sales_base[:50]
        context['today_sales'] = sales_base.filter(sale_date__date=today).aggregate(
            total=Sum('final_amount'), count=Count('id')
        )
        context['week_sales'] = sales_base.filter(sale_date__date__gte=week_ago).aggregate(
            total=Sum('final_amount'), count=Count('id')
        )
        context['month_sales'] = sales_base.filter(sale_date__date__gte=month_ago).aggregate(
            total=Sum('final_amount'), count=Count('id')
        )

        return context


class PharmacyReportsView(PharmacyRequiredMixin, TemplateView):  # View pharmacy reports and statistics
    template_name = "pharmacy/reports.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from pharmacy.models import PharmacySale, PharmacyInventory, PharmacyOrder
        from django.db.models import Sum, Count, Avg
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        month_ago = today - timedelta(days=30)

        sales_data = PharmacySale.objects.filter(
            pharmacy_id=self.request.user.uid,
            sale_date__date__gte=month_ago
        ).aggregate(
            total_revenue=Sum('final_amount'),
            total_sales=Count('id'),
            avg_sale=Avg('final_amount')
        )

        inventory_data = PharmacyInventory.objects.filter(
            pharmacy_id=self.request.user.uid
        ).aggregate(
            total_items=Count('id'),
            low_stock=Count('id', filter=models.Q(quantity_in_stock__lte=models.F('reorder_level')))
        )

        orders_data = PharmacyOrder.objects.filter(
            pharmacy_id=self.request.user.uid,
            order_date__date__gte=month_ago
        ).aggregate(
            total_orders=Count('id'),
            pending_orders=Count('id', filter=models.Q(status='pending'))
        )

        context['sales_data'] = sales_data
        context['inventory_data'] = inventory_data
        context['orders_data'] = orders_data

        return context


class PharmacyProfileView(PharmacyRequiredMixin, TemplateView):  # View and edit pharmacy profile information
    template_name = "pharmacy/profile.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        participant = self.request.user

        try:
            provider_data = participant.provider_data
        except:
            provider_data = None

        from core.models import LegalRepresentative
        try:
            context['legal_representative'] = LegalRepresentative.objects.get(participant=participant)
        except LegalRepresentative.DoesNotExist:
            context['legal_representative'] = None

        context['participant'] = participant
        context['provider_data'] = provider_data
        return context

    def post(self, request, *args, **kwargs):  # Handle form submission for data updates
        from django.http import JsonResponse
        import json

        try:
            data = json.loads(request.body)
            action = data.get('action')

            participant = request.user

            if action == 'update_profile':
                participant.full_name = data.get('full_name', participant.full_name)
                participant.phone_number = data.get('phone_number', participant.phone_number)
                participant.address = data.get('address', participant.address)
                participant.city = data.get('city', participant.city)
                participant.country = data.get('country', participant.country)
                participant.save()

                try:
                    provider_data = participant.provider_data
                    provider_data.provider_name = data.get('provider_name', provider_data.provider_name)
                    provider_data.license_number = data.get('license_number', provider_data.license_number)
                    provider_data.registration_number = data.get('registration_number', provider_data.registration_number)
                    provider_data.address = data.get('provider_address', provider_data.address)
                    provider_data.city = data.get('provider_city', provider_data.city)
                    provider_data.state = data.get('state', provider_data.state)
                    provider_data.country = data.get('provider_country', provider_data.country)
                    provider_data.postal_code = data.get('postal_code', provider_data.postal_code)
                    provider_data.phone_number = data.get('provider_phone', provider_data.phone_number)
                    provider_data.email = data.get('provider_email', provider_data.email)
                    provider_data.website = data.get('website', provider_data.website)

                    services = data.get('services_offered')
                    if services:
                        provider_data.services_offered = services if isinstance(services, list) else [services]

                    hours = data.get('operating_hours')
                    if hours:
                        provider_data.operating_hours = hours if isinstance(hours, dict) else {}

                    provider_data.save()
                except Exception as e:
                    pass

                return JsonResponse({'success': True, 'message': 'Profil mis à jour avec succès'})

            return JsonResponse({'success': False, 'error': 'Action invalide'}, status=400)

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class PharmacySettingsView(PharmacyRequiredMixin, TemplateView):  # Pharmacy account settings and preferences
    template_name = "shared/settings.html"
    
    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.preferences_utils import get_or_create_preferences
        context['preferences'] = get_or_create_preferences(self.request.user)
        return context


class PharmacyServicesView(PharmacyRequiredMixin, TemplateView):  # Class for pharmacyservices
    template_name = "pharmacy/services.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.models import ParticipantService

        services = ParticipantService.objects.filter(
            participant=self.request.user, is_active=True
        ).order_by("-created_at")

        context["services"] = services
        context["total_services"] = services.count()
        context["active_services"] = services.filter(is_available=True).count()

        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):  # Handle form submission for data updates
        try:
            from core.models import ParticipantService
            from decimal import Decimal

            data = json.loads(request.body)
            action = data.get("action")

            if action == "create":
                ParticipantService.objects.create(
                    participant=request.user,
                    name=data.get("name"),
                    category=data.get("category"),
                    description=data.get("description", ""),
                    price=Decimal(str(data.get("price"))),
                    currency=data.get("currency", "XOF"),
                    duration_minutes=data.get("duration_minutes"),
                    is_active=True,
                    is_available=True,
                )
                return JsonResponse(
                    {"success": True, "message": "Service ajouté avec succès"}
                )

            elif action == "update":
                service = ParticipantService.objects.get(
                    id=data.get("service_id"), participant=request.user
                )
                service.name = data.get("name", service.name)
                service.category = data.get("category", service.category)
                service.description = data.get("description", service.description)
                if "price" in data:
                    service.price = Decimal(str(data.get("price")))
                service.currency = data.get("currency", service.currency)
                service.duration_minutes = data.get(
                    "duration_minutes", service.duration_minutes
                )
                service.is_available = data.get("is_available", service.is_available)
                service.save()

                return JsonResponse(
                    {"success": True, "message": "Service modifié avec succès"}
                )

            elif action == "delete":
                service = ProviderService.objects.get(
                    id=data.get("service_id"), participant=request.user
                )
                service.is_active = False
                service.save()

                return JsonResponse(
                    {"success": True, "message": "Service désactivé avec succès"}
                )

            return JsonResponse(
                {"success": False, "message": "Action invalide"}, status=400
            )

        except ProviderService.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Service introuvable"}, status=404
            )
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)


class PharmacyStaffManagementView(PharmacyRequiredMixin, TemplateView):  # Class for pharmacystaffmanagement
    template_name = "pharmacy/staff/staff_list.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from pharmacy.models import PharmacyStaff, PharmacyCounter
        
        # Get all staff for this pharmacy
        staff_members = PharmacyStaff.objects.filter(
            pharmacy=self.request.user,
        ).select_related('staff_participant').order_by('-created_at')
        
        # Get counters
        counters = PharmacyCounter.objects.filter(
            pharmacy=self.request.user,
            is_active=True
        ).order_by('counter_number')
        
        # Calculate stats
        total_staff = staff_members.count()
        active_staff = staff_members.filter(is_active=True).count()
        
        context.update({
            'staff_members': staff_members,
            'counters': counters,
            'total_staff': total_staff,
            'active_staff': active_staff,
        })
        
        return context


class PharmacyBonusConfigView(PharmacyRequiredMixin, TemplateView):  # Class for pharmacybonusconfig
    template_name = "pharmacy/bonus_configs.html"


class InsuranceClaimsView(InsuranceRequiredMixin, TemplateView):  # View insurance claims
    template_name = "insurance/claims.html"


class PatientInsuranceClaimsView(PatientRequiredMixin, TemplateView):  # Patient view for insurance claims
    template_name = "patient/insurance_claims.html"


class PatientInsuranceInvoicesView(PatientRequiredMixin, TemplateView):  # Patient view for insurance invoices
    template_name = "patient/insurance_invoices.html"


class InsuranceValidationView(InsuranceRequiredMixin, TemplateView):  # Class for insurancevalidation
    template_name = "insurance/validation.html"


class InsuranceStaffManagementView(InsuranceRequiredMixin, TemplateView):  # Class for insurancestaffmanagement
    template_name = "insurance/staff.html"


class InsuranceStaffDashboardView(TemplateView):  # Dashboard for insurance staff members
    template_name = "insurance/staff_dashboard.html"
    
    def get(self, request, *args, **kwargs):
        participant = request.user
        
        # Check if participant is insurance staff
        if participant.role != 'insurance_company' or not participant.staff_role:
            messages.error(request, "Accès refusé. Réservé au personnel d'assurance.")
            return redirect('/')
        
        if not participant.affiliated_provider_id:
            messages.error(request, "Aucune affiliation trouvée. Contactez l'administrateur.")
            return redirect('/')
        
        # Get insurance company
        try:
            from core.models import Participant
            insurance_company = Participant.objects.get(
                uid=participant.affiliated_provider_id,
                role='insurance_company'
            )
        except Participant.DoesNotExist:
            messages.error(request, "Compagnie d'assurance non trouvée.")
            return redirect('/')
        
        context = self.get_context_data(**kwargs)
        context['staff_participant'] = participant
        context['insurance_company'] = insurance_company
        context['staff_role'] = participant.staff_role
        
        return self.render_to_response(context)


class InsuranceEnquiriesView(InsuranceRequiredMixin, TemplateView):  # Class for insuranceenquiries
    template_name = "insurance/enquiries.html"


class InsurancePoliciesView(InsuranceRequiredMixin, TemplateView):  # Class for insurancepolicies
    template_name = "insurance/policies.html"


class InsuranceMembersView(InsuranceRequiredMixin, TemplateView):  # View insurance members
    template_name = "insurance/members.html"


class InsurancePaymentsView(InsuranceRequiredMixin, TemplateView):  # Class for insurancepayments
    template_name = "insurance/payments.html"


class InsuranceNetworkView(InsuranceRequiredMixin, TemplateView):  # Class for insurancenetwork
    template_name = "insurance/network.html"


class InsuranceReportsView(InsuranceRequiredMixin, TemplateView):  # View insurance reports and statistics
    template_name = "insurance/reports.html"


class InsuranceProfileView(InsuranceRequiredMixin, TemplateView):  # View and edit insurance company profile
    template_name = "insurance/profile.html"
    
    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.models import LegalRepresentative
        try:
            context['legal_representative'] = LegalRepresentative.objects.get(participant=self.request.user)
        except LegalRepresentative.DoesNotExist:
            context['legal_representative'] = None
        return context


class InsuranceSettingsView(InsuranceRequiredMixin, TemplateView):  # Insurance company account settings
    template_name = "shared/settings.html"
    
    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        from core.preferences_utils import get_or_create_preferences
        context['preferences'] = get_or_create_preferences(self.request.user)
        return context


class WalletView(LoginRequiredMixin, TemplateView):  # Class for wallet
    template_name = "wallet/banking_wallet.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)
        portal = self.request.path.split("/")[1]
        context["portal"] = portal

        from .models import Wallet, Transaction

        try:
            wallet = Wallet.objects.get(participant=self.request.user)
            context["balance"] = wallet.balance
            context["currency"] = wallet.currency

            total_income = (
                Transaction.objects.filter(
                    wallet=wallet, transaction_type="deposit"
                ).aggregate(total=db_models.Sum("amount"))["total"]
                or 0
            )
            context["total_income"] = total_income

            total_expenses = (
                Transaction.objects.filter(
                    wallet=wallet,
                    transaction_type__in=["payment", "withdrawal", "transfer"],
                ).aggregate(total=db_models.Sum("amount"))["total"]
                or 0
            )
            context["total_expenses"] = total_expenses

            pending_transactions = Transaction.objects.filter(
                wallet=wallet, status="pending"
            )
            pending_amount = (
                pending_transactions.aggregate(total=db_models.Sum("amount"))["total"]
                or 0
            )
            context["pending_amount"] = pending_amount / 100
            context["pending_count"] = pending_transactions.count()

        except Wallet.DoesNotExist:
            context["balance"] = 0
            context["currency"] = "EUR"
            context["total_income"] = 0
            context["total_expenses"] = 0
            context["pending_amount"] = 0
            context["pending_count"] = 0

        return context


class TransactionsView(LoginRequiredMixin, TemplateView):  # Class for transactions
    template_name = "wallet/transactions.html"
    login_url = "/auth/login/"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            context = super().get_context_data(**kwargs)
            portal = self.request.path.split("/")[1]
            context["portal"] = portal

            from payments.models import ServiceTransaction, PaymentReceipt
            from appointments.models import Appointment
            from core.models import Transaction as CoreTransaction
            from django.db.models import Q, Sum, Case, When, DecimalField
            from .geolocation_service import GeolocationService
            from currency_converter.services import CurrencyConverterService
            from decimal import Decimal

            # Get patient's local currency based on country code and geolocation
            patient_currency = None

            # Try to get currency from patient's phone country code
            if self.request.user.role == 'patient':
                try:
                    from core.models import ParticipantPhone
                    phone = ParticipantPhone.objects.filter(
                        participant=self.request.user,
                        is_verified=True
                    ).first()
                    if phone and phone.country:
                        patient_currency = CurrencyConverterService.get_currency_from_country(phone.country)
                except Exception:
                    pass

            # Fallback to geolocation-based currency
            if not patient_currency:
                patient_currency = GeolocationService.get_currency_for_request(self.request)

            # Final fallback to base currency
            if not patient_currency:
                patient_currency = CurrencyConverterService.BASE_CURRENCY

            display_currency = patient_currency
            context["display_currency"] = display_currency
            context["currency"] = display_currency

            # Get all transactions for this patient
            if self.request.user.role == 'patient':
                from core.models import Transaction as CoreTransaction
                
                # Get ServiceTransaction records
                service_transactions = ServiceTransaction.objects.filter(
                    patient=self.request.user
                ).select_related('service_provider', 'gateway_transaction')

                # Get CoreTransaction records (includes FedaPay direct payments)
                core_transactions = CoreTransaction.objects.filter(
                    Q(sender=self.request.user) | Q(recipient=self.request.user)
                ).select_related('wallet', 'sender', 'recipient')

                # Get Appointments with payment info
                appointments = Appointment.objects.filter(
                    patient=self.request.user,
                    payment_status__in=['paid', 'pending', 'partial']
                ).select_related('doctor', 'hospital')

                # Combine all transactions
                all_transactions = []

                # Add ServiceTransaction records with currency conversion
                for txn in service_transactions:
                    # Convert amount to patient's local currency
                    original_amount = txn.amount
                    original_currency = txn.currency or 'XOF'

                    try:
                        converted_amount = CurrencyConverterService.convert_amount(
                            Decimal(str(original_amount)),
                            original_currency,
                            display_currency
                        )
                    except Exception:
                        converted_amount = original_amount

                    all_transactions.append({
                        'type': 'service_transaction',
                        'transaction_ref': txn.transaction_ref,
                        'created_at': txn.created_at,
                        'service_type': txn.service_type,
                        'service_type_display': txn.get_service_type_display(),
                        'service_description': txn.service_description,
                        'payment_method': txn.get_payment_method_display(),
                        'amount': converted_amount,
                        'original_amount': original_amount,
                        'original_currency': original_currency,
                        'currency': display_currency,
                        'status': txn.status,
                        'status_display': txn.get_status_display(),
                    })

                # Add CoreTransaction records (FedaPay direct payments, etc.)
                for txn in core_transactions:
                    # Skip wallet-based transactions (already in ServiceTransaction)
                    if txn.wallet is not None:
                        continue
                    
                    # Determine if this is incoming or outgoing
                    is_incoming = txn.recipient == self.request.user
                    original_amount = txn.amount
                    original_currency = txn.currency or 'XOF'

                    try:
                        converted_amount = CurrencyConverterService.convert_amount(
                            Decimal(str(original_amount)),
                            original_currency,
                            display_currency
                        )
                    except Exception:
                        converted_amount = original_amount

                    # Get service description from metadata
                    service_description = txn.description or ''
                    if txn.metadata:
                        if isinstance(txn.metadata, dict):
                            service_type = txn.metadata.get('service_type', txn.transaction_type)
                            service_description = txn.metadata.get('service_description', service_description) or service_description
                        else:
                            service_type = txn.transaction_type
                    else:
                        service_type = txn.transaction_type

                    # Map transaction status
                    status = txn.status  # pending, completed, failed, cancelled
                    status_display = status.replace('_', ' ').title()

                    all_transactions.append({
                        'type': 'core_transaction',
                        'transaction_ref': txn.transaction_ref,
                        'created_at': txn.created_at,
                        'service_type': service_type,
                        'service_type_display': service_type.replace('_', ' ').title(),
                        'service_description': service_description,
                        'payment_method': txn.payment_method.replace('_', ' ').title() if txn.payment_method else 'Online Payment',
                        'amount': converted_amount,
                        'original_amount': original_amount,
                        'original_currency': original_currency,
                        'currency': display_currency,
                        'status': status,
                        'status_display': status_display,
                        'is_incoming': is_incoming,
                    })

                # Add Appointments as transactions with currency conversion
                for appt in appointments:
                    status = 'completed' if appt.payment_status == 'paid' else 'pending'
                    status_display = 'Completed' if appt.payment_status == 'paid' else 'Pending'
                    provider = appt.doctor.full_name if appt.doctor else (appt.hospital.full_name if appt.hospital else 'N/A')
                    txn_ref = f"APT-{appt.created_at.strftime('%Y%m%d%H%M%S')}-{str(appt.id)[:8].upper()}"

                    # Convert appointment fee to patient's local currency
                    original_amount = appt.consultation_fee or Decimal('0.00')
                    original_currency = 'XOF'  # Default currency for appointments

                    try:
                        converted_amount = CurrencyConverterService.convert_amount(
                            original_amount,
                            original_currency,
                            display_currency
                        )
                    except Exception:
                        converted_amount = original_amount

                    all_transactions.append({
                        'type': 'appointment',
                        'transaction_ref': txn_ref,
                        'created_at': appt.created_at,
                        'service_type': 'appointment',
                        'service_type_display': appt.get_appointment_type_display() if hasattr(appt, 'get_appointment_type_display') else appt.appointment_type.replace('_', ' ').title(),
                        'service_description': f"Rendez-vous - {appt.appointment_date.strftime('%d/%m/%Y à %H:%M')}",
                        'payment_method': appt.payment_method.replace('_', ' ').title() if appt.payment_method else 'N/A',
                        'amount': converted_amount,
                        'original_amount': original_amount,
                        'original_currency': original_currency,
                        'currency': display_currency,
                        'status': status,
                        'status_display': status_display,
                    })

                # Sort by date (newest first)
                all_transactions.sort(key=lambda x: x['created_at'], reverse=True)

                # Calculate summary statistics (using converted amounts)
                total_income = Decimal('0.00')
                total_expenses = Decimal('0.00')
                pending_amount = Decimal('0.00')

                for txn in all_transactions:
                    amount = Decimal(str(txn['amount']))
                    if txn['status'] == 'completed':
                        total_expenses += amount
                    elif txn['status'] == 'pending':
                        pending_amount += amount

                context['total_income'] = total_income
                context['total_expenses'] = total_expenses
                context['pending_amount'] = pending_amount
                context['net_balance'] = total_income - total_expenses

                # Get payment receipts
                receipts = PaymentReceipt.objects.filter(
                    issued_to=self.request.user
                ).select_related('service_transaction', 'issued_by')

                transaction_to_invoice = {}
                for receipt in receipts:
                    if receipt.service_transaction:
                        transaction_to_invoice[receipt.service_transaction.transaction_ref] = receipt.id

                context['transaction_to_invoice'] = transaction_to_invoice
                context['transactions'] = all_transactions
            else:
                context['transactions'] = []
                context['total_income'] = 0
                context['total_expenses'] = 0
                context['pending_amount'] = 0
                context['net_balance'] = 0
                context['transaction_to_invoice'] = {}

            return context
        except Exception as e:
            logger.error(f"Error in TransactionsView: {str(e)}", exc_info=True)
            # Return safe defaults
            context = super().get_context_data(**kwargs)
            context.update({
                'portal': self.request.path.split("/")[1] if "/" in self.request.path else 'patient',
                'transactions': [],
                'total_income': 0,
                'total_expenses': 0,
                'pending_amount': 0,
                'net_balance': 0,
                'transaction_to_invoice': {},
                'display_currency': 'XOF',
                'currency': 'XOF',
                'error_message': 'Unable to load transactions. Please try again later.'
            })
            return context


class PatientWalletView(PatientRequiredMixin, TemplateView):  # Class for patientwallet
    template_name = "wallet/banking_wallet.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)

        from payments.models import (
            PaymentRequest,
            ServiceTransaction,
            ParticipantGatewayAccount,
            FinancialChat,
        )
        from .geolocation_service import GeolocationService

        display_currency = GeolocationService.get_currency_for_request(self.request)
        context["display_currency"] = display_currency
        context["currency"] = display_currency

        transactions = ServiceTransaction.objects.filter(
            db_models.Q(patient=self.request.user) |
            db_models.Q(service_participant=self.request.user)
        ).select_related(
            'patient', 'service_provider', 'gateway_transaction', 'fee_details'
        ).order_by("-created_at")[:20]

        for txn in transactions:
            is_incoming = txn.service_provider == self.request.user
            txn.is_incoming = is_incoming

            if txn.currency != display_currency:
                try:
                    txn.display_amount = CurrencyConverterService.convert_amount(
                        txn.amount, txn.currency, display_currency
                    )
                    txn.display_currency = display_currency
                except:
                    txn.display_amount = txn.amount
                    txn.display_currency = txn.currency
            else:
                txn.display_amount = txn.amount
                txn.display_currency = txn.currency

        context["transactions"] = transactions

        patient_transactions = ServiceTransaction.objects.filter(
            patient=self.request.user, status="completed"
        )
        total_paid = patient_transactions.aggregate(
            total=db_models.Sum("amount")
        )["total"] or 0

        if display_currency != "XOF" and total_paid > 0:
            try:
                total_paid = CurrencyConverterService.convert_amount(
                    Decimal(str(total_paid)), "XOF", display_currency
                )
            except:
                pass
        context["total_paid"] = total_paid

        provider_transactions = ServiceTransaction.objects.filter(
            service_participant=self.request.user, status="completed"
        ).prefetch_related('fee_details')

        total_earned = Decimal('0')
        for txn in provider_transactions:
            if hasattr(txn, 'fee_details') and txn.fee_details:
                total_earned += txn.fee_details.net_amount_to_provider
            else:
                total_earned += txn.amount

        if display_currency != "XOF" and total_earned > 0:
            try:
                total_earned = CurrencyConverterService.convert_amount(
                    total_earned, "XOF", display_currency
                )
            except:
                pass
        context["total_earned"] = total_earned

        pending_transactions = ServiceTransaction.objects.filter(
            db_models.Q(patient=self.request.user) |
            db_models.Q(service_participant=self.request.user),
            status="pending"
        )
        context["pending_count"] = pending_transactions.count()

        context["payment_requests_sent"] = PaymentRequest.objects.filter(
            from_participant=self.request.user
        ).order_by("-created_at")[:10]
        context["payment_requests_received"] = PaymentRequest.objects.filter(
            to_participant=self.request.user
        ).order_by("-created_at")[:10]

        context["gateway_accounts"] = ParticipantGatewayAccount.objects.filter(
            participant=self.request.user
        ).order_by("-is_default", "-created_at")

        context["financial_chats"] = FinancialChat.objects.filter(
            participant=self.request.user
        ).order_by("-created_at")[:10]

        return context


class MyAppointmentsView(PatientRequiredMixin, TemplateView):  # Class for myappointments
    template_name = "patient/my_appointments.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)

        from appointments.models import Appointment
        from datetime import date

        upcoming_appointments = (
            Appointment.objects.filter(
                patient=self.request.user,
                status__in=["pending", "confirmed", "in_progress"],
                appointment_date__gte=date.today(),
            )
            .select_related("doctor")
            .order_by("appointment_date", "appointment_time")
        )

        past_appointments = (
            Appointment.objects.filter(
                patient=self.request.user,
                status__in=["completed", "cancelled", "no_show"],
            )
            .select_related("doctor")
            .order_by("-appointment_date", "-appointment_time")[:20]
        )

        context["upcoming_appointments"] = upcoming_appointments
        context["past_appointments"] = past_appointments
        context["upcoming_count"] = upcoming_appointments.count()

        return context


class AIAssistantView(PatientRequiredMixin, TemplateView):  # Class for aiassistant
    template_name = "patient/ai_assistant.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)

        from ai.models import AIHealthInsight

        participant = self.request.user

        recent_insights = AIHealthInsight.objects.filter(patient=participant).order_by(
            "-generated_at"
        )[:5]

        context["recent_insights"] = recent_insights
        context["has_insights"] = recent_insights.exists()

        return context


class HealthRecordsView(PatientRequiredMixin, TemplateView):  # Class for healthrecords
    template_name = "patient/health_records.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)

        from health_records.models import HealthRecord, DocumentUpload, WearableData

        patient = self.request.user

        health_records = HealthRecord.objects.filter(assigned_to=patient).order_by(
            "-date_of_record"
        )[:10]

        documents = DocumentUpload.objects.filter(uploaded_by=patient).order_by(
            "-uploaded_at"
        )[:10]

        recent_vitals = WearableData.objects.filter(patient=patient).order_by("-timestamp")[
            :5
        ]

        context["health_records"] = health_records
        context["documents"] = documents
        context["recent_vitals"] = recent_vitals
        context["total_records"] = health_records.count()

        return context


class PrescriptionsView(PatientRequiredMixin, TemplateView):  # Class for prescriptions
    template_name = "patient/prescriptions.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)

        from prescriptions.models import Prescription, PrescriptionFulfillment
        from datetime import date

        patient = self.request.user

        active_prescriptions = (
            Prescription.objects.filter(
                patient=patient, status="active", valid_until__gte=date.today()
            )
            .select_related("doctor")
            .prefetch_related("items")
            .order_by("-issue_date")
        )

        expired_prescriptions = (
            Prescription.objects.filter(patient=patient, valid_until__lt=date.today())
            .select_related("doctor")
            .order_by("-valid_until")[:10]
        )

        pending_fulfillments = (
            PrescriptionFulfillment.objects.filter(
                prescription__patient=patient, status="pending"
            )
            .select_related("prescription", "pharmacy")
            .order_by("-created_at")
        )

        context["active_prescriptions"] = active_prescriptions
        context["expired_prescriptions"] = expired_prescriptions
        context["pending_fulfillments"] = pending_fulfillments
        context["active_count"] = active_prescriptions.count()

        return context


class TelemedicineView(PatientRequiredMixin, TemplateView):  # Class for telemedicine
    template_name = "patient/telemedicine.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            context = super().get_context_data(**kwargs)

            from doctor.models import DoctorData
            from core.models import Participant
            from appointments.models import Appointment
            from django.db.models import Q
            from datetime import datetime, date

            # Get all doctors available for telemedicine
            doctors = (
                Participant.objects.filter(
                    role="doctor",
                    is_active=True,
                    doctor_data__is_available_for_telemedicine=True,
                )
                .select_related("doctor_data")
                .order_by("-doctor_data__rating")
            )

            # Update ratings from actual reviews for accurate display
            for doctor in doctors:
                try:
                    doctor.doctor_data.update_rating_cache()
                except Exception as e:
                    logger.warning(f"Could not update rating for doctor {doctor.id}: {str(e)}")

            context["doctors"] = doctors

            # Get upcoming telemedicine appointments
            upcoming_appointments = (
                Appointment.objects.filter(
                    patient=self.request.user,
                    type="telemedicine",
                    status__in=["pending", "confirmed"],
                    appointment_date__gte=date.today(),
                )
                .select_related("doctor")
                .order_by("appointment_date", "appointment_time")[:5]
            )

            context["upcoming_appointments"] = upcoming_appointments

            # Get previous telemedicine consultations
            previous_consultations = (
                Appointment.objects.filter(
                    patient=self.request.user,
                    type="telemedicine",
                    status__in=["completed", "cancelled"],
                )
                .select_related("doctor")
                .order_by("-appointment_date", "-appointment_time")[:10]
            )

            context["previous_consultations"] = previous_consultations

            # Get specializations for filter
            specializations = DoctorData.SPECIALIZATION_CHOICES
            context["specializations"] = specializations

            return context
        except Exception as e:
            logger.error(f"Error in TelemedicineView: {str(e)}", exc_info=True)
            # Return safe defaults
            context = super().get_context_data(**kwargs)
            context.update({
                'doctors': [],
                'upcoming_appointments': [],
                'previous_consultations': [],
                'specializations': [],
                'error_message': 'Unable to load telemedicine data. Please try again later.'
            })
            return context


class ConsultationFeedbackView(PatientRequiredMixin, TemplateView):
    """View for patients to rate and review consultations after completion"""
    template_name = "patient/consultation_feedback.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from appointments.models import Appointment
        from core.models import Review

        appointment_id = self.kwargs.get('appointment_id')

        try:
            appointment = Appointment.objects.select_related('doctor').get(
                id=appointment_id,
                patient=self.request.user
            )
            context['appointment'] = appointment

            # Check if already reviewed
            existing_review = Review.objects.filter(
                reviewer=self.request.user,
                appointment_id=appointment_id
            ).first()

            context['existing_review'] = existing_review

        except Appointment.DoesNotExist:
            context['error'] = 'Appointment not found'

        return context

    def post(self, request, *args, **kwargs):
        """Handle feedback submission"""
        from appointments.models import Appointment
        from core.models import Review
        from django.shortcuts import redirect
        from django.contrib import messages

        appointment_id = self.kwargs.get('appointment_id')

        try:
            appointment = Appointment.objects.select_related('doctor').get(
                id=appointment_id,
                patient=request.user
            )

            # Get form data
            rating = int(request.POST.get('rating', 5))
            review_text = request.POST.get('review_text', '').strip()
            professionalism_rating = request.POST.get('professionalism_rating')
            communication_rating = request.POST.get('communication_rating')
            wait_time_rating = request.POST.get('wait_time_rating')
            value_rating = request.POST.get('value_rating')

            # Determine service type
            service_type = 'telemedicine' if appointment.type == 'telemedicine' else 'consultation'

            # Create or update review
            review, created = Review.objects.update_or_create(
                reviewer=request.user,
                appointment_id=appointment_id,
                defaults={
                    'reviewed_type': 'doctor',
                    'reviewed_id': appointment.doctor.uid,
                    'rating': rating,
                    'service_type': service_type,
                    'review_text': review_text,
                    'professionalism_rating': int(professionalism_rating) if professionalism_rating else None,
                    'communication_rating': int(communication_rating) if communication_rating else None,
                    'wait_time_rating': int(wait_time_rating) if wait_time_rating else None,
                    'value_rating': int(value_rating) if value_rating else None,
                    'is_verified': True,  # Auto-verify since it's post-appointment
                }
            )

            # Update doctor's cached rating
            appointment.doctor.doctor_data.update_rating_cache()

            messages.success(request, 'Merci pour votre avis! Votre évaluation a été soumise avec succès.')
            return redirect('patient:telemedicine')

        except Appointment.DoesNotExist:
            messages.error(request, 'Rendez-vous introuvable.')
            return redirect('patient:telemedicine')
        except Exception as e:
            messages.error(request, f'Erreur lors de la soumission: {str(e)}')
            return redirect('patient:telemedicine')


class InsuranceSubscriptionView(PatientRequiredMixin, TemplateView):  # Class for insurancesubscription
    template_name = "patient/insurance_subscription.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            context = super().get_context_data(**kwargs)

            from insurance.models import (
                InsurancePackage,
                PatientInsuranceCard,
                InsuranceClaim,
            )

            user = self.request.user

            available_packages = (
                InsurancePackage.objects.filter(is_active=True)
                .select_related("company")
                .order_by("premium_amount")
            )
            
            logger.info(f"Found {available_packages.count()} active insurance packages")

            user_insurance_cards = (
                PatientInsuranceCard.objects.filter(
                    patient=user, status__in=["active", "pending"]
                )
                .select_related("insurance_package")
                .order_by("-issue_date")
            )

            recent_claims = (
                InsuranceClaim.objects.filter(patient=user)
                .select_related("insurance_package")
                .order_by("-submission_date")[:5]
            )

            context["available_packages"] = available_packages
            context["user_insurance_cards"] = user_insurance_cards
            context["recent_claims"] = recent_claims
            context["has_active_insurance"] = user_insurance_cards.filter(
                status="active"
            ).exists()

            return context
        except Exception as e:
            logger.error(f"Error in InsuranceSubscriptionView: {str(e)}", exc_info=True)
            # Return safe defaults
            context = super().get_context_data(**kwargs)
            context.update({
                'available_packages': [],
                'user_insurance_cards': [],
                'recent_claims': [],
                'has_active_insurance': False,
                'error_message': 'Unable to load insurance data. Please try again later.'
            })
            return context


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BookAppointmentView(PatientRequiredMixin, TemplateView):  # Class for bookappointment
    template_name = "patient/book_appointment.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)

        from core.models import Participant, ProviderData
        from doctor.models import DoctorData

        doctors = (
            Participant.objects.filter(role="doctor", is_active=True)
            .select_related("doctor_data")
            .order_by("doctor_data__specialization")
        )

        hospitals = Participant.objects.filter(
            role="hospital", is_active=True
        ).select_related("provider_data")

        specializations = DoctorData.SPECIALIZATION_CHOICES

        context["doctors"] = doctors
        context["hospitals"] = hospitals
        context["specializations"] = specializations

        return context


class RescheduleAppointmentView(PatientRequiredMixin, TemplateView):  # Class for rescheduleappointment
    template_name = "patient/reschedule_appointment.html"

    def get_context_data(self, **kwargs):  # Add additional context data for template rendering
        context = super().get_context_data(**kwargs)

        from datetime import date
        from django.conf import settings
        from appointments.models import Appointment
        from doctor.models import DoctorData
        from core.models import Participant

        appointment_id = self.kwargs.get("appointment_id")

        try:
            appointment = Appointment.objects.select_related(
                "doctor", "doctor__doctor_data"
            ).get(id=appointment_id, patient=self.request.user)
            context["appointment"] = appointment
        except Appointment.DoesNotExist:
            context["appointment"] = None

        doctors = (
            Participant.objects.filter(role="doctor", is_active=True)
            .select_related("doctor_data")
            .order_by("doctor_data__specialization")
        )

        specializations = DoctorData.SPECIALIZATION_CHOICES

        context["doctors"] = doctors
        context["specializations"] = specializations
        context["today"] = date.today()
        context["reschedule_fee"] = getattr(settings, "RESCHEDULE_FEE", 1000)

        return context


class ServiceParticipantsView(PatientRequiredMixin, TemplateView):
    template_name = "patient/service_participants.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from core.models import Participant

        hospitals = (
            Participant.objects.filter(role="hospital", is_active=True)
            .select_related("provider_data")
            .order_by("provider_data__provider_name")
        )

        pharmacies = (
            Participant.objects.filter(role="pharmacy", is_active=True)
            .select_related("provider_data")
            .order_by("provider_data__provider_name")
        )

        doctors = (
            Participant.objects.filter(role="doctor", is_active=True)
            .select_related("doctor_data")
            .order_by("doctor_data__specialization")
        )

        context["hospitals"] = hospitals
        context["pharmacies"] = pharmacies
        context["doctors"] = doctors

        return context


class BookTelemedicineView(PatientRequiredMixin, View):  # Class for booktelemedicine
    def post(self, request):  # Handle form submission for data updates
        from appointments.models import Appointment
        from datetime import datetime
        from django.utils import timezone

        try:
            doctor_id = request.POST.get("doctor_id")
            appointment_date = request.POST.get("appointment_date")
            appointment_time = request.POST.get("appointment_time")
            reason = request.POST.get("reason", "")
            symptoms = request.POST.get("symptoms", "")

            if not all([doctor_id, appointment_date, appointment_time, reason]):
                messages.error(
                    request, "Tous les champs obligatoires doivent être remplis."
                )
                return redirect("patient:telemedicine")

            doctor = Participant.objects.get(uid=doctor_id, role="doctor")

            appointment_datetime = datetime.strptime(
                f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M"
            )

            if appointment_datetime <= timezone.now():
                messages.error(
                    request, "La date et l'heure doivent être dans le futur."
                )
                return redirect("patient:telemedicine")

            appointment = Appointment.objects.create(
                patient=request.user,
                doctor=doctor,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                type="telemedicine",
                status="pending",
                reason=reason,
                symptoms=symptoms,
                consultation_fee=doctor.doctor_data.consultation_fee,
                original_price=doctor.doctor_data.consultation_fee,
                final_price=doctor.doctor_data.consultation_fee,
                payment_status="pending",
            )

            messages.success(
                request, "Votre demande de consultation a été envoyée avec succès!"
            )
            return redirect("patient:my_appointments")

        except Participant.DoesNotExist:
            messages.error(request, "Médecin non trouvé.")
            return redirect("patient:telemedicine")
        except ValueError:
            messages.error(request, "Format de date ou heure invalide.")
            return redirect("patient:telemedicine")
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")
            return redirect("patient:telemedicine")

@extend_schema(tags=['Patient Profile'])
class PatientProfileAPIView(APIView):  # Class for patientprofileapi
    permission_classes = [IsAuthenticated]
    serializer_class = ParticipantProfileSerializer

    @extend_schema(
        summary="Get patient profile",
        responses={200: ParticipantProfileSerializer}
    )
    def get(self, request):  # Handle get operation
        try:
            profile_data = {
                'address': request.user.address or '',
                'phone': request.user.phone or '',
                'email': request.user.email or '',
                'full_name': request.user.full_name or '',
            }

            return Response(
                {"success": True, "profile": profile_data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request):  # Handle form submission for data updates
        try:
            # Get or create patient_data
            patient_data, created = PatientData.objects.get_or_create(
                participant=request.user
            )

            # Update fields
            data = request.data
            patient_data.marital_status = data.get("marital_status", "")
            patient_data.number_of_children = data.get("number_of_children", 0)
            patient_data.profession = data.get("profession", "")
            patient_data.blood_type = data.get("blood_type", "")
            patient_data.height = data.get("height")
            patient_data.weight = data.get("weight")
            patient_data.allergies = data.get("allergies", [])
            patient_data.chronic_conditions = data.get("chronic_conditions", [])
            patient_data.current_medications = data.get("current_medications", [])
            patient_data.medical_history = data.get("medical_history", "")
            patient_data.save()

            return Response(
                {"message": "Profile updated successfully", "success": True},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"message": str(e), "success": False},
                status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(tags=['Beneficiaries'])
class BeneficiariesAPIView(APIView):  # Class for beneficiariesapi
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List all beneficiaries for the current patient",
        responses={200: CoreDependentProfileSerializer(many=True)}
    )
    def get(self, request):  # Handle get operation
        from patient.models import DependentProfile
        from core.serializers import DependentProfileSerializer

        beneficiaries = DependentProfile.objects.filter(
            patient=request.user, is_active=True
        ).order_by("-created_at")

        serializer = DependentProfileSerializer(beneficiaries, many=True)
        return Response(
            {
                "success": True,
                "beneficiaries": serializer.data,
                "count": beneficiaries.count(),
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Add a new beneficiary",
        request=CoreDependentProfileSerializer,
        responses={201: CoreDependentProfileSerializer}
    )
    def post(self, request):  # Handle form submission for data updates
        from patient.models import DependentProfile
        from core.serializers import CoreDependentProfileSerializer

        try:
            serializer = CoreDependentProfileSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(patient=request.user)
                return Response(
                    {
                        "success": True,
                        "message": "Bénéficiaire ajouté avec succès",
                        "beneficiary": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {"success": False, "message": "Données invalides", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(tags=['Beneficiaries'])
class BeneficiaryDetailAPIView(APIView):  # Class for beneficiarydetailapi
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get beneficiary details",
        responses={200: CoreDependentProfileSerializer}
    )
    def get(self, request, pk):  # Handle get operation
        from patient.models import DependentProfile
        from core.serializers import CoreDependentProfileSerializer

        try:
            beneficiary = DependentProfile.objects.get(
                id=pk, patient=request.user, is_active=True
            )
            serializer = CoreDependentProfileSerializer(beneficiary)
            return Response(
                {"success": True, "beneficiary": serializer.data},
                status=status.HTTP_200_OK,
            )
        except DependentProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Beneficiary not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @extend_schema(
        summary="Update beneficiary",
        request=CoreDependentProfileSerializer,
        responses={200: CoreDependentProfileSerializer}
    )
    def put(self, request, pk):  # Handle put operation
        from patient.models import DependentProfile
        from core.serializers import CoreDependentProfileSerializer

        try:
            beneficiary = DependentProfile.objects.get(
                id=pk, patient=request.user, is_active=True
            )
            serializer = CoreDependentProfileSerializer(
                beneficiary, data=request.data, partial=True, context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "success": True,
                        "message": "Bénéficiaire mis à jour avec succès",
                        "beneficiary": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"success": False, "message": "Données invalides", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DependentProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Bénéficiaire introuvable"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @extend_schema(
        summary="Delete/deactivate beneficiary",
        responses={200: OpenApiResponse(description="Success")}
    )
    def delete(self, request, pk):  # Handle delete operation
        from patient.models import DependentProfile

        try:
            beneficiary = DependentProfile.objects.get(
                id=pk, patient=request.user, is_active=True
            )
            beneficiary.is_active = False
            beneficiary.save()
            return Response(
                {"success": True, "message": "Beneficiary removed successfully"},
                status=status.HTTP_200_OK,
            )
        except DependentProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Beneficiary not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

            patient_data.insurance_provider = data.get("insurance_provider", "")
            patient_data.insurance_policy_number = data.get(
                "insurance_policy_number", ""
            )

            patient_data.save()

            return Response(
                {"success": True, "message": "Profil mis à jour avec succès"}
            )
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=400)


class PatientHospitalsView(PatientRequiredMixin, TemplateView):  # Class for patienthospitals
    template_name = "patient/hospitals.html"


@extend_schema(tags=['Hospitals'])
class HospitalsAPIView(APIView):  # Class for hospitalsapi
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List all hospitals with optional search and sorting",
        parameters=[
            OpenApiParameter(name='search', description='Search term', required=False, type=str),
            OpenApiParameter(name='sort_by', description='Sort field (name, city)', required=False, type=str)
        ],
        responses={200: HospitalProfileSerializer(many=True)}
    )
    def get(self, request):  # Handle get operation
        from core.models import Participant
        from core.serializers import HospitalProfileSerializer
        from django.db.models import Q

        search = request.query_params.get('search', '').strip()
        sort_by = request.query_params.get('sort_by', 'name')

        hospitals = Participant.objects.filter(
            role='hospital',
            is_active=True
        )

        if search:
            hospitals = hospitals.filter(
                Q(full_name__icontains=search) |
                Q(address__icontains=search) |
                Q(city__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )

        if sort_by == 'name':
            hospitals = hospitals.order_by('full_name')
        elif sort_by == 'city':
            hospitals = hospitals.order_by('city', 'full_name')
        else:
            hospitals = hospitals.order_by('full_name')

        serializer = HospitalProfileSerializer(hospitals, many=True)
        return Response(
            {
                "success": True,
                "hospitals": serializer.data,
                "count": hospitals.count(),
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Hospital Appointments"])
class HospitalAppointmentsAPIView(APIView):  # Class for hospitalappointmentsapi
    permission_classes = [IsAuthenticated]
    serializer_class = ParticipantSerializer

    @extend_schema(
        summary="Book hospital appointment",
        request=ParticipantSerializer,
        responses={200: ParticipantSerializer}
    )
    def post(self, request):  # Handle form submission for data updates
        from appointments.models import Appointment
        from core.models import Participant
        from patient.models import DependentProfile

        try:
            # Log received data for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Appointment booking request data: {request.data}")
            
            hospital_id = request.data.get('hospital_id')
            appointment_date = request.data.get('appointment_date')
            appointment_time = request.data.get('appointment_time')
            service_type = request.data.get('service_type')
            reason = request.data.get('reason')
            beneficiary_id = request.data.get('beneficiary_id')

            logger.info(f"Parsed values - hospital: {hospital_id}, date: {appointment_date}, time: {appointment_time}")

            # Validate required fields
            if not hospital_id:
                return Response(
                    {"success": False, "error": "ID de l'hôpital manquant", "message": "Erreur: Hôpital non spécifié"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not appointment_date:
                return Response(
                    {"success": False, "error": "Date manquante", "message": "Veuillez sélectionner une date"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not appointment_time:
                return Response(
                    {"success": False, "error": "Heure manquante", "message": "Veuillez sélectionner une heure"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if hospital exists and is active
            try:
                hospital = Participant.objects.get(
                    uid=hospital_id,
                    role='hospital',
                    is_active=True
                )
            except Participant.DoesNotExist:
                return Response(
                    {"success": False, "error": "Hôpital non trouvé"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Check if slot is already booked
            slot_taken = Appointment.objects.filter(
                hospital=hospital,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                status__in=['pending', 'confirmed', 'in_progress']
            ).exists()

            if slot_taken:
                return Response(
                    {
                        "success": False,
                        "error": "Ce créneau horaire est déjà réservé",
                        "message": "Veuillez choisir un autre horaire disponible"
                    },
                    status=status.HTTP_409_CONFLICT
                )

            # Create appointment
            appointment = Appointment.objects.create(
                patient=request.user,
                hospital=hospital,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                appointment_type=service_type or 'consultation',
                reason=reason or '',
                status='pending',
                payment_status='pending',
                is_hospital_appointment=True
            )

            # If beneficiary is specified and not 'self', link it
            if beneficiary_id and beneficiary_id != 'self':
                try:
                    beneficiary = DependentProfile.objects.get(
                        id=beneficiary_id,
                        patient=request.user
                    )
                    appointment.beneficiary = beneficiary
                    appointment.save()
                except DependentProfile.DoesNotExist:
                    pass

            # Update appointment with fees
            from django.conf import settings
            from decimal import Decimal
            
            try:
                # Get consultation fee from hospital or use default
                consultation_fee = Decimal(str(getattr(hospital, 'consultation_fee', settings.DEFAULT_CONSULTATION_FEE_USD)))
                
                # Get patient's currency
                patient_currency = getattr(request.user, 'preferred_currency', 'USD')
                if hasattr(request.user, 'wallet') and request.user.wallet and request.user.wallet.preferred_currency:
                    patient_currency = request.user.wallet.preferred_currency
                
                # Convert consultation fee to patient currency
                from currency_converter.services import CurrencyConverterService
                if patient_currency != 'XOF':
                    try:
                        converted_fee = CurrencyConverterService.convert_amount(consultation_fee, 'XOF', patient_currency)
                    except Exception as e:
                        logger.error(f"Currency conversion error: {e}")
                        converted_fee = consultation_fee
                else:
                    converted_fee = consultation_fee
                
                # Update appointment with fee information
                appointment.consultation_fee = converted_fee
                appointment.currency = patient_currency
                appointment.original_price = converted_fee
                appointment.final_price = converted_fee
                appointment.save()
                
            except Exception as fee_error:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not calculate fees: {str(fee_error)}")
                # Set default values
                appointment.consultation_fee = Decimal('50.00')
                appointment.currency = 'USD'
                appointment.original_price = Decimal('50.00')
                appointment.final_price = Decimal('50.00')
                appointment.save()

            return Response(
                {
                    "success": True,
                    "message": "Rendez-vous réservé avec succès",
                    "appointment_id": str(appointment.id),
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating appointment: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            traceback.print_exc()
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "message": "Une erreur est survenue lors de la création du rendez-vous",
                    "details": traceback.format_exc() if request.user.is_staff else None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(tags=["Appointments"])
class AvailableSlotsAPIView(APIView):
    """Get available appointment slots for a doctor or hospital on a specific date"""
    permission_classes = [IsAuthenticated]
    serializer_class = ParticipantSerializer

    @extend_schema(
        summary="Get available appointment slots",
        responses={200: ParticipantSerializer}
    )
    def get(self, request):
        from appointments.models import Appointment, Availability
        from core.models import Participant
        from datetime import datetime, time, timedelta

        try:
            hospital_id = request.GET.get('hospital_id')
            doctor_id = request.GET.get('doctor_id')
            date_str = request.GET.get('date')

            if not (hospital_id or doctor_id) or not date_str:
                return Response(
                    {"success": False, "error": "Paramètres manquants (doctor_id ou hospital_id requis)"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Parse date
            try:
                appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"success": False, "error": "Format de date invalide"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get participant (doctor or hospital)
            try:
                if doctor_id:
                    participant = Participant.objects.get(
                        uid=doctor_id,
                        role='doctor',
                        is_active=True
                    )
                    participant_type = 'doctor'
                else:
                    participant = Participant.objects.get(
                        uid=hospital_id,
                        role='hospital',
                        is_active=True
                    )
                    participant_type = 'hospital'
            except Participant.DoesNotExist:
                return Response(
                    {"success": False, "error": f"{'Docteur' if doctor_id else 'Hôpital'} non trouvé"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get day of week
            weekday = appointment_date.strftime('%A').lower()
            weekday_map = {
                'monday': 'monday', 'tuesday': 'tuesday', 'wednesday': 'wednesday',
                'thursday': 'thursday', 'friday': 'friday', 'saturday': 'saturday', 'sunday': 'sunday'
            }
            weekday = weekday_map.get(weekday, 'monday')

            # Get availability for this day
            availability = Availability.objects.filter(
                participant=participant,
                weekday=weekday,
                is_active=True
            ).first()

            if not availability:
                return Response(
                    {
                        "success": True,
                        "slots": [],
                        "message": "Aucune disponibilité pour ce jour"
                    }
                )

            # Generate time slots
            slots = []
            current_time = datetime.combine(appointment_date, availability.start_time)
            end_time = datetime.combine(appointment_date, availability.end_time)
            slot_duration = timedelta(minutes=availability.slot_duration)

            # Get already booked appointments
            if participant_type == 'doctor':
                booked_times = set(
                    Appointment.objects.filter(
                        doctor=participant,
                        appointment_date=appointment_date,
                        status__in=['pending', 'confirmed', 'in_progress']
                    ).values_list('appointment_time', flat=True)
                )
            else:
                booked_times = set(
                    Appointment.objects.filter(
                        hospital=participant,
                        appointment_date=appointment_date,
                        status__in=['pending', 'confirmed', 'in_progress']
                    ).values_list('appointment_time', flat=True)
                )

            while current_time <= end_time:
                time_str = current_time.strftime('%H:%M')
                is_available = current_time.time() not in booked_times
                
                slots.append({
                    'time': time_str,
                    'available': is_available
                })
                
                current_time += slot_duration

            return Response({
                "success": True,
                "slots": slots,
                participant_type: participant.full_name,
                "date": date_str
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "message": "Erreur lors de la récupération des créneaux"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Participant.DoesNotExist:
            return Response(
                {"success": False, "message": "Hôpital non trouvé"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PatientPharmaciesView(LoginRequiredMixin, TemplateView):  # Class for patientpharmacies
    template_name = "patient/pharmacies.html"

class PharmacyCatalogView(LoginRequiredMixin, TemplateView):  # Class for pharmacycatalog
    template_name = "patient/pharmacy_catalog.html"


class CheckoutView(LoginRequiredMixin, TemplateView):  # Class for checkout
    template_name = "patient/checkout.html"


@extend_schema(tags=["Pharmacy"])
class PharmacyCatalogAPIView(APIView):  # Class for pharmacycatalogapi
    permission_classes = [IsAuthenticated]
    serializer_class = ParticipantSerializer

    @extend_schema(
        summary="Get pharmacy catalog",
        responses={200: ParticipantSerializer}
    )
    def get(self, request):  # Handle get operation
        from pharmacy.models import PharmacyInventory
        from prescriptions.models import Medication
        from django.db.models import Q

        search = request.query_params.get('search', '').strip()
        pharmacy_id = request.query_params.get('pharmacy_id', '').strip()
        category = request.query_params.get('category', '').strip()

        inventory_items = PharmacyInventory.objects.filter(
            is_publicly_available=True,
            quantity_in_stock__gt=0
        ).select_related('medication', 'pharmacy')

        if search:
            inventory_items = inventory_items.filter(
                Q(medication__name__icontains=search) |
                Q(medication__generic_name__icontains=search) |
                Q(medication__brand_name__icontains=search) |
                Q(medication__category__icontains=search)
            )

        if pharmacy_id:
            inventory_items = inventory_items.filter(pharmacy_id=pharmacy_id)

        if category:
            inventory_items = inventory_items.filter(medication__category=category)

        inventory_items = inventory_items.order_by('medication__name')

        catalog_data = []
        pharmacies_set = set()
        categories_set = set()

        for item in inventory_items:
            catalog_data.append({
                'id': str(item.id),
                'medication_id': str(item.medication.id),
                'medication_name': item.medication.name,
                'generic_name': item.medication.generic_name,
                'brand_name': item.medication.brand_name,
                'category': item.medication.category,
                'description': item.medication.description,
                'dosage_forms': item.medication.dosage_forms,
                'strengths': item.medication.strengths,
                'requires_prescription': item.medication.requires_prescription,
                'pharmacy_id': str(item.pharmacy.uid),
                'pharmacy_name': item.pharmacy.full_name,
                'pharmacy_address': item.pharmacy.address,
                'pharmacy_phone': item.pharmacy.phone_number,
                'quantity_in_stock': item.quantity_in_stock,
                'unit_price': item.unit_price,
                'selling_price': item.selling_price,
                'expiry_date': item.expiry_date.strftime('%Y-%m-%d'),
                'requires_refrigeration': item.requires_refrigeration,
            })

            pharmacies_set.add((str(item.pharmacy.uid), item.pharmacy.full_name))
            if item.medication.category:
                categories_set.add(item.medication.category)

        return Response({
            'success': True,
            'catalog': catalog_data,
            'count': len(catalog_data),
            'pharmacies': [{'id': p[0], 'name': p[1]} for p in sorted(pharmacies_set, key=lambda x: x[1])],
            'categories': sorted(list(categories_set))
        }, status=status.HTTP_200_OK)


@extend_schema(tags=["Pharmacy"])
class PharmaciesAPIView(APIView):  # Class for pharmaciesapi
    permission_classes = [IsAuthenticated]
    serializer_class = ParticipantSerializer

    @extend_schema(
        summary="Get list of pharmacies",
        responses={200: ParticipantSerializer}
    )
    def get(self, request):  # Handle get operation
        from core.models import Participant
        from core.serializers import HospitalProfileSerializer
        from django.db.models import Q

        search = request.query_params.get('search', '').strip()
        sort_by = request.query_params.get('sort_by', 'name')

        pharmacies = Participant.objects.filter(
            role='pharmacy',
            is_active=True
        )

        if search:
            pharmacies = pharmacies.filter(
                Q(full_name__icontains=search) |
                Q(address__icontains=search) |
                Q(city__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )

        if sort_by == 'name':
            pharmacies = pharmacies.order_by('full_name')
        elif sort_by == 'city':
            pharmacies = pharmacies.order_by('city', 'full_name')
        else:
            pharmacies = pharmacies.order_by('full_name')

        serializer = HospitalProfileSerializer(pharmacies, many=True)
        return Response({
            "success": True,
            "pharmacies": serializer.data,
            "count": pharmacies.count(),
        }, status=status.HTTP_200_OK)


@extend_schema(tags=["Pharmacy Orders"])
class PharmacyOrdersAPIView(APIView):  # Class for pharmacyordersapi
    permission_classes = [IsAuthenticated]
    serializer_class = ParticipantSerializer

    @extend_schema(
        summary="Create pharmacy order",
        request=ParticipantSerializer,
        responses={201: ParticipantSerializer}
    )
    def post(self, request):  # Handle form submission for data updates
        from prescriptions.models import Prescription, PrescriptionFulfillment, FulfillmentItem, PrescriptionItem
        from core.models import Participant

        try:
            pharmacy_id = request.data.get('pharmacy_id')
            prescription_id = request.data.get('prescription_id')
            medication_items = request.data.get('medication_items', [])
            delivery_address = request.data.get('delivery_address')
            delivery_phone = request.data.get('delivery_phone')
            notes = request.data.get('notes', '')

            pharmacy = Participant.objects.get(
                uid=pharmacy_id,
                role='pharmacy',
                is_active=True
            )

            prescription = Prescription.objects.get(
                id=prescription_id,
                user=request.user,
                status__in=['active', 'verified']
            )

            fulfillment = PrescriptionFulfillment.objects.create(
                prescription=prescription,
                pharmacy=pharmacy,
                status='pending',
                notes=f"{notes}\n\nDelivery Address: {delivery_address}\nDelivery Phone: {delivery_phone}"
            )

            for item_id in medication_items:
                prescription_item = PrescriptionItem.objects.get(
                    id=item_id,
                    prescription=prescription
                )

                FulfillmentItem.objects.create(
                    fulfillment=fulfillment,
                    prescription_item=prescription_item,
                    quantity_fulfilled=0,
                    quantity_remaining=prescription_item.quantity
                )

            prescription.status = 'ordered'
            prescription.save()

            return Response({
                "success": True,
                "message": "Commande envoyée avec succès",
                "order_id": str(fulfillment.id),
            }, status=status.HTTP_201_CREATED)

        except Participant.DoesNotExist:
            return Response({
                "success": False,
                "message": "Pharmacie non trouvée"
            }, status=status.HTTP_404_NOT_FOUND)
        except Prescription.DoesNotExist:
            return Response({
                "success": False,
                "message": "Ordonnance non trouvée ou invalide"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(tags=['Security Monitoring'])
class AntiScrapingMonitorViewSet(viewsets.ViewSet):  # Class for antiscrapingmonitorset
    permission_classes = [IsAuthenticated]
    serializer_class = ParticipantSerializer

    @extend_schema(summary="Get blocked IPs", responses={200: OpenApiResponse(description="List of blocked IPs")})
    @action(detail=False, methods=["get"])
    def blocked_ips(self, request):  # Handle blocked ips operation
        from .anti_scraping_monitor import AntiScrapingMonitor

        if not request.user.is_staff:
            return Response(
                {"error": "Permission refusée"}, status=status.HTTP_403_FORBIDDEN
            )

        blocked = AntiScrapingMonitor.get_blocked_ips()
        return Response({"blocked_ips": blocked, "count": len(blocked)})

    @extend_schema(summary="Get suspicious activities", responses={200: OpenApiResponse(description="List of suspicious activities")})
    @action(detail=False, methods=["get"])
    def suspicious_activities(self, request):  # Handle suspicious activities operation
        from .anti_scraping_monitor import AntiScrapingMonitor

        if not request.user.is_staff:
            return Response(
                {"error": "Permission refusée"}, status=status.HTTP_403_FORBIDDEN
            )

        hours = int(request.query_params.get("hours", 24))
        activities = AntiScrapingMonitor.get_suspicious_activities(hours)
        return Response(
            {"activities": activities, "count": len(activities), "hours": hours}
        )

    @extend_schema(summary="Unblock IP address", responses={200: OpenApiResponse(description="IP unblocked")})
    @action(detail=False, methods=["post"])
    def unblock_ip(self, request):  # Handle unblock ip operation
        from .anti_scraping_monitor import AntiScrapingMonitor

        if not request.user.is_staff:
            return Response(
                {"error": "Permission refusée"}, status=status.HTTP_403_FORBIDDEN
            )

        ip = request.data.get("ip")
        if not ip:
            return Response({"error": "IP requise"}, status=status.HTTP_400_BAD_REQUEST)

        AntiScrapingMonitor.unblock_ip(ip)
        return Response({"success": True, "message": f"IP {ip} débloquée avec succès"})

    @action(detail=False, methods=["get"])
    def ip_stats(self, request):  # Handle ip stats operation
        from .anti_scraping_monitor import AntiScrapingMonitor

        if not request.user.is_staff:
            return Response(
                {"error": "Permission refusée"}, status=status.HTTP_403_FORBIDDEN
            )

        ip = request.query_params.get("ip")
        if not ip:
            return Response({"error": "IP requise"}, status=status.HTTP_400_BAD_REQUEST)

        stats = AntiScrapingMonitor.get_ip_statistics(ip)
        return Response(stats)


@extend_schema(tags=['Security Monitoring'])
class SecurityMonitorViewSet(viewsets.ViewSet):  # Class for securitymonitorset
    permission_classes = [IsAuthenticated]
    serializer_class = ParticipantSerializer

    @extend_schema(summary="Get security events", responses={200: OpenApiResponse(description="Security events list")})
    @action(detail=False, methods=["get"])
    def security_events(self, request):  # Handle security events operation
        from .security_monitor import SecurityMonitor

        if not request.user.is_staff:
            return Response(
                {"error": "Permission refusée"}, status=status.HTTP_403_FORBIDDEN
            )

        hours = int(request.query_params.get("hours", 24))
        severity = request.query_params.get("severity", None)

        events = SecurityMonitor.get_security_events(hours, severity)

        return Response(
            {
                "events": events,
                "count": len(events),
                "hours": hours,
                "severity_filter": severity,
            }
        )

    @extend_schema(summary="Get attack statistics", responses={200: OpenApiResponse(description="Attack statistics")})


    @action(detail=False, methods=["get"])


    def attack_statistics(self, request):  # Handle attack statistics operation
        from .security_monitor import SecurityMonitor

        if not request.user.is_staff:
            return Response(
                {"error": "Permission refusée"}, status=status.HTTP_403_FORBIDDEN
            )

        stats = SecurityMonitor.get_attack_statistics()
        return Response(stats)

    @extend_schema(summary="Get blocked IPs summary", responses={200: OpenApiResponse(description="Blocked IPs summary")})


    @action(detail=False, methods=["get"])


    def blocked_ips_summary(self, request):  # Handle blocked ips summary operation
        from .security_monitor import SecurityMonitor

        if not request.user.is_staff:
            return Response(
                {"error": "Permission refusée"}, status=status.HTTP_403_FORBIDDEN
            )

        summary = SecurityMonitor.get_blocked_ips_summary()
        return Response(summary)

    @extend_schema(summary="Unblock all IPs", responses={200: OpenApiResponse(description="All IPs unblocked")})


    @action(detail=False, methods=["post"])


    def unblock_ip_all(self, request):  # Handle unblock ip all operation
        from .security_monitor import SecurityMonitor

        if not request.user.is_staff:
            return Response(
                {"error": "Permission refusée"}, status=status.HTTP_403_FORBIDDEN
            )

        ip = request.data.get("ip")
        if not ip:
            return Response({"error": "IP requise"}, status=status.HTTP_400_BAD_REQUEST)

        SecurityMonitor.unblock_all_for_ip(ip)
        return Response(
            {"success": True, "message": f"Tous les blocages pour {ip} ont été levés"}
        )

    @action(detail=False, methods=["get"])
    def security_health(self, request):  # Handle security health operation
        from .security_monitor import SecurityMonitor

        if not request.user.is_staff:
            return Response(
                {"error": "Permission refusée"}, status=status.HTTP_403_FORBIDDEN
            )

        health = SecurityMonitor.get_security_health()
        return Response(health)


class PrescriptionDetailView(PharmacyRequiredMixin, DetailView):  # Class for prescriptiondetail
    template_name = "pharmacy/prescription_detail.html"
    context_object_name = "prescription"

    def get_queryset(self):  # Filter queryset to return only current user's data
        from prescriptions.models import Prescription
        return Prescription.objects.filter(
            preferred_pharmacy_id=self.request.user.id
        ).select_related('patient', 'doctor')

    def get_object(self):  # Handle get object operation
        from prescriptions.models import Prescription
        return Prescription.objects.get(
            id=self.kwargs['prescription_id'],
            preferred_pharmacy_id=self.request.user.id
        )


class ProcessPrescriptionView(PharmacyRequiredMixin, View):  # Class for processprescription
    def post(self, request, prescription_id):  # Handle form submission for data updates
        from prescriptions.models import Prescription

        try:
            prescription = Prescription.objects.get(
                id=prescription_id,
                preferred_pharmacy_id=request.user.uid,
                status='active'
            )

            prescription.status = 'ordered'
            prescription.save()

            return JsonResponse({'success': True, 'message': 'Prescription en cours de traitement'})
        except Prescription.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Prescription non trouvée ou déjà traitée'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class MarkPrescriptionReadyView(PharmacyRequiredMixin, View):  # Class for markprescriptionready
    def post(self, request, prescription_id):  # Handle form submission for data updates
        from prescriptions.models import Prescription

        try:
            prescription = Prescription.objects.get(
                id=prescription_id,
                preferred_pharmacy_id=request.user.uid,
                status='ordered'
            )

            prescription.status = 'verified'
            prescription.save()

            return JsonResponse({'success': True, 'message': 'Prescription marquée comme prête'})
        except Prescription.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Prescription non trouvée ou statut incorrect'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


class DeliverPrescriptionView(PharmacyRequiredMixin, View):  # Class for deliverprescription
    def post(self, request, prescription_id):  # Handle form submission for data updates
        from prescriptions.models import Prescription
        from django.utils import timezone

        try:
            prescription = Prescription.objects.get(
                id=prescription_id,
                preferred_pharmacy_id=request.user.uid,
                status='verified'
            )

            prescription.status = 'fulfilled'
            prescription.fulfilled_at = timezone.now()
            prescription.save()

            return JsonResponse({'success': True, 'message': 'Prescription livrée avec succès'})
        except Prescription.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Prescription non trouvée ou pas prête pour la livraison'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


@extend_schema(tags=["Contact"])
@extend_schema(
    request=ContactFormRequestSerializer,
    responses={200: ContactFormResponseSerializer},
    summary="Submit contact form",
    description="Send a contact form message to the Bintacura team"
)
class ContactFormAPIView(APIView):  # Class for contactformapi
    permission_classes = [AllowAny]

    def post(self, request):  # Handle form submission for data updates
        from django.core.mail import send_mail
        from django.conf import settings
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags

        try:
            data = request.data
            name = data.get('name', '').strip()
            email = data.get('email', '').strip()
            phone = data.get('phone', '').strip()
            subject = data.get('subject', '').strip()
            message = data.get('message', '').strip()

            if not all([name, email, subject, message]):
                return Response(
                    {'error': 'Tous les champs obligatoires doivent être remplis'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subject_labels = {
                'support': 'Support technique',
                'info': "Demande d'information",
                'partnership': 'Opportunité de partenariat',
                'feedback': "Retour d'expérience",
                'deployment': 'Déploiement au Bénin/Afrique',
                'other': 'Autre'
            }

            subject_text = subject_labels.get(subject, subject)

            notification_subject = f'[BINTACURA Contact] {subject_text} - {name}'
            notification_message = f"""
Nouveau message de contact reçu via BINTACURA

Nom: {name}
Email: {email}
Téléphone: {phone if phone else 'Non fourni'}
Sujet: {subject_text}

Message:
{message}

---
Envoyé depuis le formulaire de contact BINTACURA
Date: {timezone.now().strftime('%d/%m/%Y à %H:%M')}
            """

            send_mail(
                notification_subject,
                notification_message,
                settings.CONTACT_EMAIL,
                ['contacts@digitalconcordia.com'],
                fail_silently=False,
            )

            confirmation_subject = 'Confirmation de réception - BINTACURA'
            confirmation_message = f"""
Bonjour {name},

Nous avons bien reçu votre message concernant: {subject_text}

Notre équipe Digital Concordia examinera votre demande et vous répondra dans les plus brefs délais à l'adresse {email}.

Merci de votre intérêt pour BINTACURA.

Cordialement,
L'équipe Digital Concordia
https://www.digitalconcordia.com

---
Ceci est un email automatique, merci de ne pas y répondre.
Pour toute question, contactez-nous à contacts@digitalconcordia.com
            """

            send_mail(
                confirmation_subject,
                confirmation_message,
                settings.NO_REPLY_EMAIL,
                [email],
                fail_silently=True,
            )

            return Response(
                {'message': 'Votre message a été envoyé avec succès. Vous recevrez une confirmation par email.'},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {'error': f'Une erreur est survenue lors de l\'envoi du message: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class PatientVideoConsultationView(PatientRequiredMixin, TemplateView):
    template_name = "patient/video_consultation.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from appointments.models import Appointment
        
        appointment_id = self.kwargs.get("appointment_id")
        try:
            appointment = Appointment.objects.select_related("doctor", "doctor__doctor_data").get(
                id=appointment_id,
                patient=self.request.user,
                type="telemedicine",
                status__in=["confirmed", "in_progress"]
            )
            context["appointment"] = appointment
        except Appointment.DoesNotExist:
            context["appointment"] = None
            context["error"] = "Rendez-vous introuvable ou non disponible"
        
        return context


class DoctorVideoConsultationView(DoctorRequiredMixin, TemplateView):
    template_name = "doctor/video_consultation.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from appointments.models import Appointment
        
        appointment_id = self.kwargs.get("appointment_id")
        try:
            appointment = Appointment.objects.select_related("patient").get(
                id=appointment_id,
                doctor=self.request.user,
                type="telemedicine",
                status__in=["confirmed", "in_progress"]
            )
            context["appointment"] = appointment
        except Appointment.DoesNotExist:
            context["appointment"] = None
            context["error"] = "Rendez-vous introuvable ou non disponible"
        
        return context

