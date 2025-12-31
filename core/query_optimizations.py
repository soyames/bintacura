from django.db import models


class OptimizedQueryMixin:
    @classmethod
    def get_optimized_queryset(cls):
        return cls.objects.select_related().prefetch_related()

    @classmethod
    def get_with_related(cls, *select_fields, **prefetch_fields):
        queryset = cls.objects.all()
        if select_fields:
            queryset = queryset.select_related(*select_fields)
        if prefetch_fields:
            queryset = queryset.prefetch_related(*prefetch_fields.values())
        return queryset


def optimize_appointments_query():
    from appointments.models import Appointment

    return Appointment.objects.select_related(
        "patient", "doctor", "facility"
    ).prefetch_related("patient__insurance_cards", "doctor__doctor_data")


def optimize_prescriptions_query():
    from prescriptions.models import Prescription

    return Prescription.objects.select_related("user", "doctor").prefetch_related(
        "items__medication"
    )


def optimize_insurance_claims_query():
    from insurance.models import InsuranceClaim

    return InsuranceClaim.objects.select_related(
        "patient", "insurance_card", "insurance_card__insurance_package"
    ).prefetch_related("attachments")


def optimize_health_records_query():
    from health_records.models import HealthRecord

    return HealthRecord.objects.select_related("patient", "doctor")


def optimize_payment_query():
    from payments.models import Payment
    
    return Payment.objects.select_related(
        "participant", "service"
    ).prefetch_related("refunds")


def optimize_service_query():
    from core.models import ParticipantService
    
    return ParticipantService.objects.select_related(
        "participant", "category"
    )


def optimize_forum_post_query():
    from communication.models import ForumPost
    
    return ForumPost.objects.select_related(
        "author"
    ).prefetch_related("likes", "comments")


def optimize_refund_query():
    from core.models import RefundRequest
    
    return RefundRequest.objects.select_related(
        "patient", "payment", "approved_by"
    )
