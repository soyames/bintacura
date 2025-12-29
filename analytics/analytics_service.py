from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from appointments.models import Appointment
from prescriptions.models import Prescription
from payments.models import Transaction
from health_records.models import HealthRecord
from core.models import Participant


class PatientAnalytics:  # Provides analytics and statistics for patient dashboards
    @staticmethod
    def get_dashboard_stats(patient):  # Get comprehensive dashboard statistics for a specific patient
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)

        appointments_stats = Appointment.objects.filter(patient=patient).aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status="completed")),
            cancelled=Count("id", filter=Q(status="cancelled")),
            pending=Count("id", filter=Q(status="pending")),
            upcoming=Count(
                "id",
                filter=Q(
                    status__in=["confirmed", "pending"], appointment_date__gte=today
                ),
            ),
        )

        recent_appointments = Appointment.objects.filter(
            patient=patient, appointment_date__gte=thirty_days_ago
        ).count()

        prescriptions_stats = Prescription.objects.filter(patient=patient).aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status="active")),
            fulfilled=Count("id", filter=Q(status="fulfilled")),
        )

        health_records_count = HealthRecord.objects.filter(patient=patient).count()

        spending_stats = Transaction.objects.filter(
            patient=patient, status="completed"
        ).aggregate(
            total_spent=Sum("amount"),
            avg_transaction=Avg("amount"),
            total_transactions=Count("id"),
        )

        monthly_spending = []
        for i in range(6):
            month_start = (today.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
            next_month = (month_start + timedelta(days=32)).replace(day=1)

            amount = (
                Transaction.objects.filter(
                    patient=patient,
                    status="completed",
                    created_at__gte=month_start,
                    created_at__lt=next_month,
                ).aggregate(total=Sum("amount"))["total"]
                or 0
            )

            monthly_spending.insert(
                0, {"month": month_start.strftime("%B"), "amount": float(amount)}
            )

        return {
            "appointments": {
                "total": appointments_stats["total"] or 0,
                "completed": appointments_stats["completed"] or 0,
                "cancelled": appointments_stats["cancelled"] or 0,
                "pending": appointments_stats["pending"] or 0,
                "upcoming": appointments_stats["upcoming"] or 0,
                "recent_30_days": recent_appointments,
            },
            "prescriptions": {
                "total": prescriptions_stats["total"] or 0,
                "active": prescriptions_stats["active"] or 0,
                "fulfilled": prescriptions_stats["fulfilled"] or 0,
            },
            "health_records": {"total": health_records_count},
            "spending": {
                "total": float(spending_stats["total_spent"] or 0),
                "average": float(spending_stats["avg_transaction"] or 0),
                "transactions": spending_stats["total_transactions"] or 0,
                "monthly": monthly_spending,
            },
        }


class DoctorAnalytics:  # DoctorAnalytics class implementation
    @staticmethod
    def get_dashboard_stats(doctor):  # Get dashboard stats
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)

        appointments_stats = Appointment.objects.filter(doctor=doctor).aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status="completed")),
            cancelled=Count("id", filter=Q(status="cancelled")),
            pending=Count("id", filter=Q(status="pending")),
            today=Count(
                "id",
                filter=Q(appointment_date=today, status__in=["confirmed", "pending"]),
            ),
        )

        recent_appointments = Appointment.objects.filter(
            doctor=doctor, appointment_date__gte=thirty_days_ago
        ).count()

        patients_stats = (
            Appointment.objects.filter(doctor=doctor, status="completed")
            .values("patient")
            .distinct()
            .count()
        )

        revenue_stats = Transaction.objects.filter(
            doctor=doctor, status="completed"
        ).aggregate(
            total_revenue=Sum("amount"),
            avg_consultation=Avg("amount"),
            total_transactions=Count("id"),
        )

        monthly_revenue = []
        monthly_patients = []
        for i in range(6):
            month_start = (today.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
            next_month = (month_start + timedelta(days=32)).replace(day=1)

            revenue = (
                Transaction.objects.filter(
                    doctor=doctor,
                    status="completed",
                    created_at__gte=month_start,
                    created_at__lt=next_month,
                ).aggregate(total=Sum("amount"))["total"]
                or 0
            )

            patient_count = (
                Appointment.objects.filter(
                    doctor=doctor,
                    status="completed",
                    appointment_date__gte=month_start,
                    appointment_date__lt=next_month,
                )
                .values("patient")
                .distinct()
                .count()
            )

            monthly_revenue.insert(
                0, {"month": month_start.strftime("%B"), "amount": float(revenue)}
            )

            monthly_patients.insert(
                0, {"month": month_start.strftime("%B"), "count": patient_count}
            )

        services_stats = {}
        from core.models import ProviderService

        services = ProviderService.objects.filter(provider=doctor)
        for service in services:
            appointment_count = Appointment.objects.filter(
                doctor=doctor, service=service, status="completed"
            ).count()
            services_stats[service.name] = appointment_count

        return {
            "appointments": {
                "total": appointments_stats["total"] or 0,
                "completed": appointments_stats["completed"] or 0,
                "cancelled": appointments_stats["cancelled"] or 0,
                "pending": appointments_stats["pending"] or 0,
                "today": appointments_stats["today"] or 0,
                "recent_30_days": recent_appointments,
            },
            "patients": {"total_unique": patients_stats},
            "revenue": {
                "total": float(revenue_stats["total_revenue"] or 0),
                "average": float(revenue_stats["avg_consultation"] or 0),
                "transactions": revenue_stats["total_transactions"] or 0,
                "monthly": monthly_revenue,
            },
            "monthly_patients": monthly_patients,
            "services": services_stats,
        }


class HospitalAnalytics:  # HospitalAnalytics class implementation
    @staticmethod
    def get_dashboard_stats(hospital):  # Get dashboard stats
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)

        appointments_stats = Appointment.objects.filter(hospital=hospital).aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status="completed")),
            cancelled=Count("id", filter=Q(status="cancelled")),
            pending=Count("id", filter=Q(status="pending")),
            today=Count(
                "id",
                filter=Q(appointment_date=today, status__in=["confirmed", "pending"]),
            ),
        )

        from core.models import HospitalBed, HospitalAdmission

        beds_stats = HospitalBed.objects.filter(hospital=hospital).aggregate(
            total=Count("id"),
            available=Count("id", filter=Q(status="available")),
            occupied=Count("id", filter=Q(status="occupied")),
        )

        admissions_stats = HospitalAdmission.objects.filter(
            hospital=hospital
        ).aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status="admitted")),
            discharged=Count("id", filter=Q(status="discharged")),
        )

        staff_count = Participant.objects.filter(
            role="doctor", affiliated_provider_id=hospital.uid
        ).count()

        revenue_stats = Transaction.objects.filter(
            hospital=hospital, status="completed"
        ).aggregate(
            total_revenue=Sum("amount"),
            avg_transaction=Avg("amount"),
            total_transactions=Count("id"),
        )

        monthly_revenue = []
        for i in range(6):
            month_start = (today.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
            next_month = (month_start + timedelta(days=32)).replace(day=1)

            revenue = (
                Transaction.objects.filter(
                    hospital=hospital,
                    status="completed",
                    created_at__gte=month_start,
                    created_at__lt=next_month,
                ).aggregate(total=Sum("amount"))["total"]
                or 0
            )

            monthly_revenue.insert(
                0, {"month": month_start.strftime("%B"), "amount": float(revenue)}
            )

        services_stats = {}
        from core.models import ProviderService

        services = ProviderService.objects.filter(provider=hospital)
        for service in services:
            appointment_count = Appointment.objects.filter(
                hospital=hospital, service=service, status="completed"
            ).count()
            services_stats[service.name] = appointment_count

        return {
            "appointments": {
                "total": appointments_stats["total"] or 0,
                "completed": appointments_stats["completed"] or 0,
                "cancelled": appointments_stats["cancelled"] or 0,
                "pending": appointments_stats["pending"] or 0,
                "today": appointments_stats["today"] or 0,
            },
            "beds": {
                "total": beds_stats["total"] or 0,
                "available": beds_stats["available"] or 0,
                "occupied": beds_stats["occupied"] or 0,
                "occupancy_rate": round(
                    (beds_stats["occupied"] or 0)
                    / max(beds_stats["total"] or 1, 1)
                    * 100,
                    2,
                ),
            },
            "admissions": {
                "total": admissions_stats["total"] or 0,
                "active": admissions_stats["active"] or 0,
                "discharged": admissions_stats["discharged"] or 0,
            },
            "staff": {"count": staff_count},
            "revenue": {
                "total": float(revenue_stats["total_revenue"] or 0),
                "average": float(revenue_stats["avg_transaction"] or 0),
                "transactions": revenue_stats["total_transactions"] or 0,
                "monthly": monthly_revenue,
            },
            "services": services_stats,
        }


class PharmacyAnalytics:  # PharmacyAnalytics class implementation
    @staticmethod
    def get_dashboard_stats(pharmacy):  # Get dashboard stats
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)

        prescriptions_stats = Prescription.objects.filter(pharmacy=pharmacy).aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status="pending")),
            fulfilled=Count("id", filter=Q(status="fulfilled")),
            cancelled=Count("id", filter=Q(status="cancelled")),
        )

        recent_prescriptions = Prescription.objects.filter(
            pharmacy=pharmacy, created_at__gte=thirty_days_ago
        ).count()

        revenue_stats = Transaction.objects.filter(
            pharmacy=pharmacy, status="completed"
        ).aggregate(
            total_revenue=Sum("amount"),
            avg_transaction=Avg("amount"),
            total_transactions=Count("id"),
        )

        monthly_revenue = []
        monthly_prescriptions = []
        for i in range(6):
            month_start = (today.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
            next_month = (month_start + timedelta(days=32)).replace(day=1)

            revenue = (
                Transaction.objects.filter(
                    pharmacy=pharmacy,
                    status="completed",
                    created_at__gte=month_start,
                    created_at__lt=next_month,
                ).aggregate(total=Sum("amount"))["total"]
                or 0
            )

            prescription_count = Prescription.objects.filter(
                pharmacy=pharmacy,
                created_at__gte=month_start,
                created_at__lt=next_month,
            ).count()

            monthly_revenue.insert(
                0, {"month": month_start.strftime("%B"), "amount": float(revenue)}
            )

            monthly_prescriptions.insert(
                0, {"month": month_start.strftime("%B"), "count": prescription_count}
            )

        services_stats = {}
        from core.models import ProviderService

        services = ProviderService.objects.filter(provider=pharmacy)
        for service in services:
            services_stats[service.name] = service.price

        return {
            "prescriptions": {
                "total": prescriptions_stats["total"] or 0,
                "pending": prescriptions_stats["pending"] or 0,
                "fulfilled": prescriptions_stats["fulfilled"] or 0,
                "cancelled": prescriptions_stats["cancelled"] or 0,
                "recent_30_days": recent_prescriptions,
            },
            "revenue": {
                "total": float(revenue_stats["total_revenue"] or 0),
                "average": float(revenue_stats["avg_transaction"] or 0),
                "transactions": revenue_stats["total_transactions"] or 0,
                "monthly": monthly_revenue,
            },
            "monthly_prescriptions": monthly_prescriptions,
            "services": services_stats,
        }
