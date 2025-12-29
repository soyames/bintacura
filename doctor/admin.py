from django.contrib import admin
from .models import DoctorData


@admin.register(DoctorData)
class DoctorDataAdmin(admin.ModelAdmin):  # Admin configuration for DoctorData model
    list_display = (
        "participant",
        "specialization",
        "license_number",
        "years_of_experience",
        "consultation_fee",
        "rating",
        "is_available_for_telemedicine",
    )
    search_fields = ("participant__email", "participant__full_name", "license_number")
    list_filter = ("specialization", "is_available_for_telemedicine")
    readonly_fields = ("rating", "total_reviews", "total_consultations")
