from django.db.models import Count, Sum, Q, Avg
from django.db import transaction as db_transaction
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from core.models import Participant, Transaction, Wallet, RefundRequest
from appointments.models import Appointment
from prescriptions.models import Prescription
from insurance.models import InsuranceClaim
from .models import PlatformStatistics, UserGrowthMetrics, RevenueMetrics


class AnalyticsService:  # Provides platform-wide analytics and statistics for admin dashboard
    @staticmethod
    def get_dashboard_overview():  # Get comprehensive platform overview statistics for admin dashboard
        today = timezone.now().date()

        total_users = Participant.objects.filter(is_active=True).count()
        total_patients = Participant.objects.filter(
            role="patient", is_active=True
        ).count()
        total_doctors = Participant.objects.filter(
            role="doctor", is_active=True
        ).count()
        total_hospitals = Participant.objects.filter(
            role="hospital", is_active=True
        ).count()
        total_pharmacies = Participant.objects.filter(
            role="pharmacy", is_active=True
        ).count()
        total_insurance = Participant.objects.filter(
            role="insurance_company", is_active=True
        ).count()

        new_users_today = Participant.objects.filter(created_at__date=today).count()

        total_transactions = Transaction.objects.count()
        transaction_volume = Transaction.objects.filter(status="completed").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        platform_fees = Transaction.objects.filter(
            transaction_type="fee", status="completed"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        pending_verifications = Participant.objects.filter(
            Q(role__in=["doctor", "hospital", "pharmacy", "insurance_company"]),
            is_verified=False,
            is_active=True,
        ).count()

        verified_providers = Participant.objects.filter(
            Q(role__in=["doctor", "hospital", "pharmacy", "insurance_company"]),
            has_blue_checkmark=True,
            is_active=True,
        ).count()

        pending_refunds = RefundRequest.objects.filter(status="pending").count()
        total_refund_requests = RefundRequest.objects.count()

        total_appointments = Appointment.objects.count()
        today_appointments = Appointment.objects.filter(appointment_date=today).count()

        return {
            "total_users": total_users,
            "total_patients": total_patients,
            "total_doctors": total_doctors,
            "total_hospitals": total_hospitals,
            "total_pharmacies": total_pharmacies,
            "total_insurance": total_insurance,
            "new_users_today": new_users_today,
            "total_transactions": total_transactions,
            "transaction_volume": float(transaction_volume),
            "platform_fees": float(platform_fees),
            "pending_verifications": pending_verifications,
            "verified_providers": verified_providers,
            "pending_refunds": pending_refunds,
            "total_refund_requests": total_refund_requests,
            "total_appointments": total_appointments,
            "today_appointments": today_appointments,
        }

    @staticmethod
    def get_user_growth_data(days=30):  # Get user growth data for specified number of days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        growth_data = []
        current_date = start_date

        while current_date <= end_date:
            daily_data = {
                "date": current_date.strftime("%Y-%m-%d"),
                "new_users": Participant.objects.filter(
                    created_at__date=current_date
                ).count(),
                "total_users": Participant.objects.filter(
                    created_at__date__lte=current_date, is_active=True
                ).count(),
            }
            growth_data.append(daily_data)
            current_date += timedelta(days=1)

        return growth_data

    @staticmethod
    def get_revenue_data(days=30):  # Get revenue data
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        revenue_data = []
        current_date = start_date

        while current_date <= end_date:
            daily_revenue = Transaction.objects.filter(
                created_at__date=current_date, status="completed"
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

            daily_fees = Transaction.objects.filter(
                created_at__date=current_date,
                transaction_type="fee",
                status="completed",
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

            daily_data = {
                "date": current_date.strftime("%Y-%m-%d"),
                "revenue": float(daily_revenue),
                "fees": float(daily_fees),
            }
            revenue_data.append(daily_data)
            current_date += timedelta(days=1)

        return revenue_data

    @staticmethod
    def get_role_distribution():  # Get role distribution
        roles = (
            Participant.objects.filter(is_active=True)
            .values("role")
            .annotate(count=Count("uid"))
            .order_by("-count")
        )

        return list(roles)

    @staticmethod
    def get_recent_activities(limit=20):  # Get recent activities
        from core.models import ParticipantActivityLog

        activities = ParticipantActivityLog.objects.select_related(
            "participant"
        ).order_by("-timestamp")[:limit]

        return [
            {
                "participant": activity.participant.full_name
                or activity.participant.email,
                "activity_type": activity.activity_type,
                "description": activity.description,
                "timestamp": activity.timestamp,
            }
            for activity in activities
        ]

    @staticmethod
    def get_top_providers(limit=10):  # Get top providers
        providers = (
            Participant.objects.filter(
                Q(role__in=["doctor", "hospital", "pharmacy"]),
                is_active=True,
                has_blue_checkmark=True,
            )
            .annotate(appointment_count=Count("doctor_appointments"))
            .order_by("-appointment_count")[:limit]
        )

        return [
            {
                "name": p.full_name,
                "role": p.role,
                "email": p.email,
                "appointments": p.appointment_count,
            }
            for p in providers
        ]

    @staticmethod
    def get_geographic_distribution():  # Get geographic distribution
        distribution = (
            Participant.objects.filter(is_active=True)
            .values("city")
            .annotate(count=Count("uid"))
            .order_by("-count")[:10]
        )

        return list(distribution)
