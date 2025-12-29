from django.contrib import admin
from .models import PatientData, DependentProfile


@admin.register(PatientData)
class PatientDataAdmin(admin.ModelAdmin):  # Admin configuration for PatientData model
    list_display = (
        "participant",
        "blood_type",
        "marital_status",
        "profession",
    )
    search_fields = ("participant__email", "participant__full_name")
    list_filter = ("blood_type", "marital_status")


@admin.register(DependentProfile)
class DependentProfileAdmin(admin.ModelAdmin):  # Admin configuration for DependentProfile model
    list_display = (
        "full_name",
        "patient",
        "relationship",
        "date_of_birth",
        "gender",
        "is_active",
    )
    search_fields = ("full_name", "patient__email", "patient__full_name")
    list_filter = ("relationship", "gender", "is_active", "created_at")
    readonly_fields = ("id", "created_at", "updated_at")
