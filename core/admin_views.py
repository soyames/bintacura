from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import TemplateView, ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from core.models import (
    Participant,
    ParticipantProfile,
    InsuranceCompanyData,
    RefundRequest,
    Transaction,
    Wallet,
    AuditLogEntry,
    ParticipantActivityLog,
    AdminPermissions,
)
from doctor.models import DoctorData
from hospital.models import HospitalData
from pharmacy.models import PharmacyData
from analytics.services import AnalyticsService
from core.services import WalletService


class SuperAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):  # Checks if user is authenticated super admin
        return self.request.user.is_authenticated and (
            self.request.user.is_superuser or self.request.user.role == "super_admin"
        )

    def handle_no_permission(self):  # Redirects unauthorized users to home page
        messages.error(self.request, "You do not have permission to access this page.")
        return redirect("home")


class AdminDashboardView(SuperAdminRequiredMixin, TemplateView):
    template_name = "admin/dashboard.html"

    def get_context_data(self, **kwargs):  # Loads admin dashboard with analytics overview and recent activities
        context = super().get_context_data(**kwargs)

        overview = AnalyticsService.get_dashboard_overview()
        context.update(overview)

        context["recent_activities"] = AnalyticsService.get_recent_activities(limit=10)
        context["pending_verifications_list"] = Participant.objects.filter(
            Q(role__in=["doctor", "hospital", "pharmacy", "insurance_company"]),
            is_verified=False,
            is_active=True,
        ).select_related("doctor_data", "hospital_data", "pharmacy_data", "insurance_company_data")[:5]

        context["pending_refunds_list"] = (
            RefundRequest.objects.filter(status="pending")
            .select_related("participant")
            .order_by("-created_at")[:5]
        )

        return context


class ParticipantVerificationView(SuperAdminRequiredMixin, ListView):
    template_name = "admin/participant_verification.html"
    context_object_name = "participants"
    paginate_by = 20

    def get_queryset(self):  # Retrieves healthcare participants with filters for verification status, role and search
        queryset = (
            Participant.objects.filter(
                Q(role__in=["doctor", "hospital", "pharmacy", "insurance_company"]),
                is_active=True,
            )
            .select_related("doctor_data", "hospital_data", "pharmacy_data", "insurance_company_data")
            .order_by("-created_at")
        )

        status_filter = self.request.GET.get("status")
        if status_filter == "pending":
            queryset = queryset.filter(is_verified=False, has_blue_checkmark=False)
        elif status_filter == "verified":
            queryset = queryset.filter(is_verified=True, has_blue_checkmark=True)
        elif status_filter == "unverified":
            queryset = queryset.filter(is_verified=False)

        role_filter = self.request.GET.get("role")
        if role_filter:
            queryset = queryset.filter(role=role_filter)

        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone_number__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filter"] = self.request.GET.get("status", "")
        context["role_filter"] = self.request.GET.get("role", "")
        context["search_query"] = self.request.GET.get("search", "")

        context["pending_count"] = Participant.objects.filter(
            Q(role__in=["doctor", "hospital", "pharmacy", "insurance_company"]),
            is_verified=False,
            has_blue_checkmark=False,
            is_active=True,
        ).count()

        context["verified_count"] = Participant.objects.filter(
            Q(role__in=["doctor", "hospital", "pharmacy", "insurance_company"]),
            has_blue_checkmark=True,
            is_active=True,
        ).count()

        return context


class ParticipantDetailView(SuperAdminRequiredMixin, DetailView):
    model = Participant
    template_name = "admin/participant_detail.html"
    context_object_name = "participant"
    pk_url_kwarg = "participant_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        participant = self.object

        if participant.role == "doctor":
            context["doctor_data"] = getattr(participant, "doctor_data", None)
        elif participant.role == "hospital":
            context["hospital_data"] = getattr(participant, "hospital_data", None)
        elif participant.role == "pharmacy":
            context["pharmacy_data"] = getattr(participant, "pharmacy_data", None)
        elif participant.role == "insurance_company":
            context["insurance_data"] = getattr(
                participant, "insurance_company_data", None
            )

        context["user_profile"] = getattr(participant, "user_profile", None)
        context["wallet"] = Wallet.objects.filter(participant=participant).first()

        context["recent_transactions"] = Transaction.objects.filter(
            Q(sender=participant) | Q(recipient=participant)
        ).order_by("-created_at")[:10]

        context["activity_logs"] = ParticipantActivityLog.objects.filter(
            participant=participant
        ).order_by("-timestamp")[:10]

        return context


class ApproveParticipantView(SuperAdminRequiredMixin, View):
    def post(self, request, participant_id):  # Approves participant verification and releases held payments
        participant = get_object_or_404(Participant, uid=participant_id)

        if participant.role not in ["doctor", "hospital", "pharmacy", "insurance_company"]:
            messages.error(request, "Invalid participant type.")
            return redirect("superadmin:participant_verification")

        participant.is_verified = True
        participant.has_blue_checkmark = True
        participant.can_receive_payments = True
        participant.verified_at = timezone.now()
        participant.verified_by = request.user
        
        verification_notes = request.POST.get('notes', '')
        if verification_notes:
            participant.verification_notes = verification_notes
            
        participant.save()

        ParticipantActivityLog.objects.create(
            participant=participant,
            activity_type="verification_approved",
            description=f"Participant verified and blue checkmark granted by {request.user.email}",
        )

        AuditLogEntry.objects.create(
            participant=request.user,
            action_type="update",
            resource_type="participant_verification",
            resource_id=str(participant.uid),
            details={
                "action": "approve",
                "participant_email": participant.email,
                "participant_role": participant.role,
                "notes": verification_notes,
            },
            success=True,
        )

        from payments.payment_hold_service import release_held_payments

        released_count = release_held_payments(participant)

        messages.success(
            request,
            f"Participant {participant.full_name or participant.email} has been verified successfully. {released_count} payments released from hold.",
        )
        return redirect("superadmin:participant_detail", participant_id=participant_id)


class RejectParticipantView(SuperAdminRequiredMixin, View):
    def post(self, request, participant_id):  # Rejects participant verification with reason and logs activity
        participant = get_object_or_404(Participant, uid=participant_id)
        reason = request.POST.get("reason", "")

        if participant.role not in ["doctor", "hospital", "pharmacy", "insurance_company"]:
            messages.error(request, "Invalid participant type.")
            return redirect("superadmin:participant_verification")

        participant.is_verified = False
        participant.has_blue_checkmark = False
        participant.can_receive_payments = False
        participant.verified_at = None
        participant.verified_by = None
        participant.verification_notes = f"REJECTED: {reason}"
        participant.save()

        ParticipantActivityLog.objects.create(
            participant=participant,
            activity_type="verification_rejected",
            description=f"Verification rejected by {request.user.email}. Reason: {reason}",
        )

        AuditLogEntry.objects.create(
            participant=request.user,
            action_type="update",
            resource_type="participant_verification",
            resource_id=str(participant.uid),
            details={
                "action": "reject",
                "participant_email": participant.email,
                "participant_role": participant.role,
                "reason": reason,
            },
            success=True,
        )

        messages.warning(
            request,
            f"Participant {participant.full_name or participant.email} verification has been rejected.",
        )
        return redirect("superadmin:participant_detail", participant_id=participant_id)


class RefundManagementView(SuperAdminRequiredMixin, ListView):
    template_name = "admin/refund_management.html"
    context_object_name = "refund_requests"
    paginate_by = 20

    def get_queryset(self):
        queryset = RefundRequest.objects.select_related(
            "participant", "transaction", "admin_reviewer"
        ).order_by("-created_at")

        status_filter = self.request.GET.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(participant__full_name__icontains=search)
                | Q(participant__email__icontains=search)
                | Q(reason__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filter"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("search", "")

        context["pending_count"] = RefundRequest.objects.filter(
            status="pending"
        ).count()
        context["approved_count"] = RefundRequest.objects.filter(
            status="approved"
        ).count()
        context["rejected_count"] = RefundRequest.objects.filter(
            status="rejected"
        ).count()

        return context


class RefundDetailView(SuperAdminRequiredMixin, DetailView):
    model = RefundRequest
    template_name = "admin/refund_detail.html"
    context_object_name = "refund"
    pk_url_kwarg = "refund_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        refund = self.object

        wallet = Wallet.objects.filter(participant=refund.participant).first()
        context["wallet_balance"] = wallet.balance if wallet else Decimal("0")

        return context


class ApproveRefundView(SuperAdminRequiredMixin, View):
    def post(self, request, refund_id):  # Approves refund request and deposits amount to participant wallet
        refund = get_object_or_404(RefundRequest, id=refund_id)
        admin_notes = request.POST.get("admin_notes", "")

        if refund.status != "pending":
            messages.error(request, "This refund request has already been processed.")
            return redirect("admin:refund_detail", refund_id=refund_id)

        try:
            refund.status = "processing"
            refund.admin_reviewer = request.user
            refund.admin_notes = admin_notes
            refund.reviewed_at = timezone.now()
            refund.save()

            refund_transaction = WalletService.deposit(
                participant=refund.participant,
                amount=refund.amount,
                payment_method="refund",
                description=f"Refund approved: {refund.reason[:100]}",
                metadata={
                    "refund_request_id": str(refund.id),
                    "original_transaction_id": str(refund.transaction.id)
                    if refund.transaction
                    else None,
                    "approved_by": request.user.email,
                },
            )

            refund.refund_transaction = refund_transaction
            refund.status = "completed"
            refund.save()

            ParticipantActivityLog.objects.create(
                participant=refund.participant,
                activity_type="refund_approved",
                description=f"Refund of {refund.amount} {refund.currency} approved by {request.user.email}",
            )

            AuditLogEntry.objects.create(
                participant=request.user,
                action_type="update",
                resource_type="refund_request",
                resource_id=str(refund.id),
                details={
                    "action": "approve",
                    "amount": float(refund.amount),
                    "participant_email": refund.participant.email,
                    "notes": admin_notes,
                },
                success=True,
            )

            messages.success(
                request,
                f"Refund request approved and {refund.amount} {refund.currency} credited to participant's wallet.",
            )

        except Exception as e:
            refund.status = "pending"
            refund.save()
            messages.error(request, f"Error processing refund: {str(e)}")

        return redirect("admin:refund_detail", refund_id=refund_id)


class RejectRefundView(SuperAdminRequiredMixin, View):
    def post(self, request, refund_id):  # Rejects refund request with admin notes and logs decision
        refund = get_object_or_404(RefundRequest, id=refund_id)
        admin_notes = request.POST.get("admin_notes", "")

        if refund.status != "pending":
            messages.error(request, "This refund request has already been processed.")
            return redirect("admin:refund_detail", refund_id=refund_id)

        refund.status = "rejected"
        refund.admin_reviewer = request.user
        refund.admin_notes = admin_notes
        refund.reviewed_at = timezone.now()
        refund.save()

        ParticipantActivityLog.objects.create(
            participant=refund.participant,
            activity_type="refund_rejected",
            description=f"Refund request rejected by {request.user.email}. Reason: {admin_notes}",
        )

        AuditLogEntry.objects.create(
            participant=request.user,
            action_type="update",
            resource_type="refund_request",
            resource_id=str(refund.id),
            details={
                "action": "reject",
                "amount": float(refund.amount),
                "participant_email": refund.participant.email,
                "notes": admin_notes,
            },
            success=True,
        )

        messages.warning(request, "Refund request has been rejected.")
        return redirect("admin:refund_detail", refund_id=refund_id)


class AnalyticsDashboardView(SuperAdminRequiredMixin, TemplateView):
    template_name = "admin/analytics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        overview = AnalyticsService.get_dashboard_overview()
        context.update(overview)

        user_growth = AnalyticsService.get_user_growth_data(days=30)
        revenue_data = AnalyticsService.get_revenue_data(days=30)
        role_distribution = AnalyticsService.get_role_distribution()

        context["user_growth_data"] = json.dumps(user_growth)
        context["revenue_data"] = json.dumps(revenue_data)
        context["role_distribution"] = json.dumps(role_distribution)
        context["top_providers"] = AnalyticsService.get_top_providers(limit=10)
        context["geographic_distribution"] = (
            AnalyticsService.get_geographic_distribution()
        )

        return context


class UserManagementView(SuperAdminRequiredMixin, ListView):
    template_name = "admin/user_management.html"
    context_object_name = "users"
    paginate_by = 25

    def get_queryset(self):
        queryset = Participant.objects.select_related("user_profile").order_by(
            "-created_at"
        )

        role_filter = self.request.GET.get("role")
        if role_filter:
            queryset = queryset.filter(role=role_filter)

        status_filter = self.request.GET.get("status")
        if status_filter == "active":
            queryset = queryset.filter(is_active=True)
        elif status_filter == "inactive":
            queryset = queryset.filter(is_active=False)
        elif status_filter == "verified":
            queryset = queryset.filter(is_verified=True)
        elif status_filter == "unverified":
            queryset = queryset.filter(is_verified=False)

        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone_number__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["role_filter"] = self.request.GET.get("role", "")
        context["status_filter"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("search", "")

        context["total_users"] = Participant.objects.count()
        context["active_users"] = Participant.objects.filter(is_active=True).count()
        context["verified_users"] = Participant.objects.filter(is_verified=True).count()

        return context


class UserDetailView(SuperAdminRequiredMixin, DetailView):
    model = Participant
    template_name = "admin/user_detail.html"
    context_object_name = "user"
    pk_url_kwarg = "user_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object

        context["user_profile"] = getattr(user, "user_profile", None)
        context["wallet"] = Wallet.objects.filter(participant=user).first()

        context["transactions"] = Transaction.objects.filter(
            Q(sender=user) | Q(recipient=user)
        ).order_by("-created_at")[:20]

        context["activity_logs"] = ParticipantActivityLog.objects.filter(
            participant=user
        ).order_by("-timestamp")[:20]

        if user.role == "doctor":
            context["doctor_data"] = getattr(user, "doctor_data", None)
        elif user.role in ["hospital", "pharmacy"]:
            context["provider_data"] = getattr(user, "provider_data", None)
        elif user.role == "insurance_company":
            context["insurance_data"] = getattr(user, "insurance_company_data", None)

        return context


class ToggleUserStatusView(SuperAdminRequiredMixin, View):
    def post(self, request, user_id):  # Activates or deactivates user account and logs action
        user = get_object_or_404(Participant, uid=user_id)

        user.is_active = not user.is_active
        user.save()

        status_text = "activated" if user.is_active else "deactivated"

        ParticipantActivityLog.objects.create(
            participant=user,
            activity_type=f"account_{status_text}",
            description=f"Account {status_text} by admin {request.user.email}",
        )

        AuditLogEntry.objects.create(
            participant=request.user,
            action_type="update",
            resource_type="user_status",
            resource_id=str(user.uid),
            details={"action": status_text, "user_email": user.email},
            success=True,
        )

        messages.success(request, f"User {user.email} has been {status_text}.")
        return redirect("admin:user_detail", user_id=user_id)


class AuditLogsView(SuperAdminRequiredMixin, ListView):
    template_name = "admin/audit_logs.html"
    context_object_name = "logs"
    paginate_by = 50

    def get_queryset(self):
        queryset = AuditLogEntry.objects.select_related("user").order_by("-timestamp")

        action_filter = self.request.GET.get("action")
        if action_filter:
            queryset = queryset.filter(action_type=action_filter)

        resource_filter = self.request.GET.get("resource")
        if resource_filter:
            queryset = queryset.filter(resource_type=resource_filter)

        user_email = self.request.GET.get("user")
        if user_email:
            queryset = queryset.filter(participant__email__icontains=user_email)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action_filter"] = self.request.GET.get("action", "")
        context["resource_filter"] = self.request.GET.get("resource", "")
        context["user_filter"] = self.request.GET.get("user", "")

        return context


class FinancialDashboardView(SuperAdminRequiredMixin, TemplateView):
    template_name = "admin/financial_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        total_revenue = Transaction.objects.filter(status="completed").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        platform_fees = Transaction.objects.filter(
            transaction_type="fee", status="completed"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        total_refunds = RefundRequest.objects.filter(status="completed").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        total_wallet_balance = Wallet.objects.aggregate(total=Sum("balance"))[
            "total"
        ] or Decimal("0")

        appointment_revenue = Transaction.objects.filter(
            transaction_type="appointment", status="completed"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        prescription_revenue = Transaction.objects.filter(
            transaction_type="prescription", status="completed"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        insurance_revenue = Transaction.objects.filter(
            transaction_type="insurance", status="completed"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        total_wallets = Wallet.objects.count()
        active_wallets = Wallet.objects.filter(balance__gt=0).count()

        total_deposits = Transaction.objects.filter(
            transaction_type="deposit", status="completed"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        total_withdrawals = Transaction.objects.filter(
            transaction_type="withdrawal", status="completed"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        context["total_revenue"] = total_revenue
        context["platform_fees"] = platform_fees
        context["total_refunds"] = total_refunds
        context["total_wallet_balance"] = total_wallet_balance
        context["appointment_revenue"] = appointment_revenue
        context["prescription_revenue"] = prescription_revenue
        context["insurance_revenue"] = insurance_revenue
        context["total_wallets"] = total_wallets
        context["active_wallets"] = active_wallets
        context["total_deposits"] = total_deposits
        context["total_withdrawals"] = total_withdrawals

        context["recent_transactions"] = Transaction.objects.select_related(
            "sender", "recipient"
        ).order_by("-created_at")[:20]

        revenue_data = AnalyticsService.get_revenue_data(days=30)
        transaction_chart_data = [
            {"date": item["date"], "volume": item["revenue"]} for item in revenue_data
        ]
        context["transaction_chart_data"] = json.dumps(transaction_chart_data)

        return context


class AdminManagementView(SuperAdminRequiredMixin, ListView):
    template_name = "admin/admin_management.html"
    context_object_name = "admins"
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            Participant.objects.filter(Q(role="admin") | Q(role="super_admin"))
            .select_related("admin_permissions")
            .order_by("-created_at")
        )

        level_filter = self.request.GET.get("level")
        if level_filter:
            queryset = queryset.filter(admin_level=level_filter)

        status_filter = self.request.GET.get("status")
        if status_filter == "active":
            queryset = queryset.filter(is_active=True)
        elif status_filter == "inactive":
            queryset = queryset.filter(is_active=False)

        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) | Q(email__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["level_filter"] = self.request.GET.get("level", "")
        context["status_filter"] = self.request.GET.get("status", "")
        context["search_query"] = self.request.GET.get("search", "")

        context["total_admins"] = Participant.objects.filter(
            Q(role="admin") | Q(role="super_admin")
        ).count()
        context["active_admins"] = Participant.objects.filter(
            Q(role="admin") | Q(role="super_admin"), is_active=True
        ).count()
        context["super_admins"] = Participant.objects.filter(role="super_admin").count()

        return context


class CreateAdminView(SuperAdminRequiredMixin, View):
    def get(self, request):  # Displays admin creation form with available admin levels
        context = {
            "admin_levels": Participant.ADMIN_LEVEL_CHOICES,
        }
        return render(request, "admin/create_admin.html", context)

    def post(self, request):  # Creates new admin user with specified permissions level
        email = request.POST.get("email")
        full_name = request.POST.get("full_name")
        admin_level = request.POST.get("admin_level")
        password = request.POST.get("password")

        if Participant.objects.filter(email=email).exists():
            messages.error(request, "A user with this email already exists.")
            return redirect("superadmin:create_admin")

        admin_user = Participant.objects.create_user(
            email=email,
            password=password,
            role="admin",
            full_name=full_name,
            admin_level=admin_level,
            is_active=True,
            is_staff=True,
        )

        AdminPermissions.objects.create(participant=admin_user)

        AuditLogEntry.objects.create(
            participant=request.user,
            action_type="create",
            resource_type="admin_user",
            resource_id=str(admin_user.uid),
            description=f"Created admin account for {email}",
        )

        messages.success(request, f"Admin account created successfully for {email}")
        return redirect("superadmin:admin_detail", admin_id=admin_user.uid)


class AdminDetailView(SuperAdminRequiredMixin, DetailView):
    model = Participant
    template_name = "admin/admin_detail.html"
    context_object_name = "admin_user"
    pk_url_kwarg = "admin_id"

    def get_queryset(self):
        return Participant.objects.filter(
            Q(role="admin") | Q(role="super_admin")
        ).select_related("admin_permissions")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        admin_user = self.object

        context["permissions"] = getattr(admin_user, "admin_permissions", None)

        context["activity_logs"] = ParticipantActivityLog.objects.filter(
            participant=admin_user
        ).order_by("-timestamp")[:20]

        context["audit_logs"] = AuditLogEntry.objects.filter(participant=admin_user).order_by(
            "-timestamp"
        )[:20]

        return context


class UpdateAdminPermissionsView(SuperAdminRequiredMixin, View):
    def post(self, request, admin_id):  # Updates admin permissions based on form submission
        admin_user = get_object_or_404(
            Participant.objects.filter(Q(role="admin") | Q(role="super_admin")),
            uid=admin_id,
        )

        permissions, created = AdminPermissions.objects.get_or_create(
            participant=admin_user
        )

        permissions.full_system_access = request.POST.get("full_system_access") == "on"
        permissions.payment_system_access = (
            request.POST.get("payment_system_access") == "on"
        )
        permissions.user_management = request.POST.get("user_management") == "on"
        permissions.analytics_access = request.POST.get("analytics_access") == "on"
        permissions.audit_access = request.POST.get("audit_access") == "on"
        permissions.provider_verification = (
            request.POST.get("provider_verification") == "on"
        )
        permissions.insurance_management = (
            request.POST.get("insurance_management") == "on"
        )
        permissions.content_moderation = request.POST.get("content_moderation") == "on"
        permissions.system_configuration = (
            request.POST.get("system_configuration") == "on"
        )
        permissions.api_management = request.POST.get("api_management") == "on"
        permissions.database_access = request.POST.get("database_access") == "on"
        permissions.compliance_monitoring = (
            request.POST.get("compliance_monitoring") == "on"
        )
        permissions.financial_reports = request.POST.get("financial_reports") == "on"
        permissions.emergency_access = request.POST.get("emergency_access") == "on"

        permissions.save()

        AuditLogEntry.objects.create(
            participant=request.user,
            action_type="update",
            resource_type="admin_permissions",
            resource_id=str(admin_user.uid),
            description=f"Updated permissions for admin {admin_user.email}",
        )

        messages.success(request, "Admin permissions updated successfully.")
        return redirect("superadmin:admin_detail", admin_id=admin_id)


class PromoteToAdminView(SuperAdminRequiredMixin, View):
    def post(self, request, user_id):  # Promotes regular user to admin with specified level
        user = get_object_or_404(Participant, uid=user_id)

        if user.role in ["admin", "super_admin"]:
            messages.warning(request, "User is already an admin.")
            return redirect("superadmin:user_detail", user_id=user_id)

        admin_level = request.POST.get("admin_level", "admin")

        user.role = "admin"
        user.admin_level = admin_level
        user.is_staff = True
        user.save()

        AdminPermissions.objects.get_or_create(participant=user)

        ParticipantActivityLog.objects.create(
            participant=user,
            activity_type="promoted_to_admin",
            description=f"Promoted to admin by {request.user.email}",
        )

        AuditLogEntry.objects.create(
            participant=request.user,
            action_type="update",
            resource_type="user_role",
            resource_id=str(user.uid),
            description=f"Promoted {user.email} to admin with level {admin_level}",
        )

        messages.success(request, "User promoted to admin successfully.")
        return redirect("superadmin:admin_detail", admin_id=user_id)


class RevokeAdminView(SuperAdminRequiredMixin, View):
    def post(self, request, admin_id):  # Revokes admin privileges and reverts user to previous role
        admin_user = get_object_or_404(Participant, uid=admin_id)

        if admin_user.role == "super_admin":
            messages.error(request, "Cannot revoke super admin privileges.")
            return redirect("superadmin:admin_detail", admin_id=admin_id)

        previous_role = request.POST.get("revert_to_role", "patient")

        admin_user.role = previous_role
        admin_user.admin_level = ""
        admin_user.is_staff = False
        admin_user.save()

        if hasattr(admin_user, "admin_permissions"):
            admin_user.admin_permissions.delete()

        ParticipantActivityLog.objects.create(
            participant=admin_user,
            activity_type="admin_revoked",
            description=f"Admin privileges revoked by {request.user.email}",
        )

        AuditLogEntry.objects.create(
            participant=request.user,
            action_type="update",
            resource_type="user_role",
            resource_id=str(admin_user.uid),
            description=f"Revoked admin privileges for {admin_user.email}",
        )

        messages.success(request, "Admin privileges revoked successfully.")
        return redirect("superadmin:user_detail", user_id=admin_id)

