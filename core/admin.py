from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Participant,
    ParticipantProfile,
    ProviderData,
    InsuranceCompanyData,
    AdminPermissions,
    StaffPermissions,
    AuditLogEntry,
    ParticipantActivityLog,
    Wallet,
    Transaction,
    RefundRequest,
    FeatureFlagConfig,
    RegionalConfiguration,
    ParticipantPreferences,
    EmergencyContact,
    LegalRepresentative,
)
from .hospital_staff_models import HospitalStaffAffiliation, StaffPermission
from patient.models import PatientData, DependentProfile
from doctor.models import DoctorData


@admin.register(Participant)
class ParticipantAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "full_name",
        "role",
        "is_active",
        "is_verified",
        "created_at",
    )
    list_filter = (
        "role",
        "is_active",
        "is_verified",
        "is_email_verified",
        "has_blue_checkmark",
    )
    search_fields = ("email", "full_name", "phone_number")
    ordering = ("-created_at",)

    fieldsets = (
        ("Authentication", {"fields": ("email", "password")}),
        (
            "Personal Info",
            {
                "fields": (
                    "full_name",
                    "phone_number",
                    "date_of_birth",
                    "gender",
                    "profile_picture_url",
                )
            },
        ),
        ("Location", {"fields": ("address", "city", "country")}),
        (
            "Role & Status",
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_verified",
                    "is_email_verified",
                    "has_blue_checkmark",
                )
            },
        ),
        (
            "Staff Info",
            {
                "fields": (
                    "affiliated_provider_id",
                    "staff_role",
                    "department_id",
                    "supervisor_id",
                    "employee_id",
                )
            },
        ),
        (
            "Admin Info",
            {"fields": ("admin_level", "department", "is_staff", "is_superuser")},
        ),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Timestamps", {"fields": ("created_at", "last_login_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "role", "full_name"),
            },
        ),
    )


@admin.register(ParticipantProfile)
class ParticipantProfileAdmin(admin.ModelAdmin):
    list_display = ("participant", "full_name", "gender", "city", "country")
    search_fields = ("full_name", "phone_number", "city")
    list_filter = ("gender", "country")

# PatientData, DoctorData, and DependentProfile admin classes moved to patient and doctor apps

@admin.register(ProviderData)
class ProviderDataAdmin(admin.ModelAdmin):
    list_display = (
        "provider_name",
        "provider_type",
        "city",
        "emergency_services",
        "rating",
    )
    search_fields = ("provider_name", "license_number", "city")
    list_filter = ("provider_type", "emergency_services", "country")


@admin.register(InsuranceCompanyData)
class InsuranceCompanyDataAdmin(admin.ModelAdmin):
    list_display = ("company_name", "license_number", "city", "country")
    search_fields = ("company_name", "license_number")
    list_filter = ("country",)


@admin.register(AdminPermissions)
class AdminPermissionsAdmin(admin.ModelAdmin):
    list_display = (
        "participant",
        "full_system_access",
        "participant_management",
        "financial_reports",
    )
    search_fields = ("participant__email",)
    list_filter = ("full_system_access", "payment_system_access", "participant_management")


@admin.register(StaffPermissions)
class StaffPermissionsAdmin(admin.ModelAdmin):
    list_display = (
        "participant",
        "can_manage_appointments",
        "can_view_patient_records",
        "can_prescribe_medication",
    )
    search_fields = ("participant__email",)


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = ("participant", "action_type", "resource_type", "timestamp", "success")
    list_filter = ("action_type", "resource_type", "success", "timestamp")
    search_fields = ("participant__email", "resource_id")
    readonly_fields = (
        "participant",
        "action_type",
        "resource_type",
        "resource_id",
        "timestamp",
        "ip_address",
        "user_agent",
        "details",
        "success",
        "error_message",
    )


@admin.register(ParticipantActivityLog)
class ParticipantActivityLogAdmin(admin.ModelAdmin):
    list_display = ("participant", "activity_type", "timestamp")
    list_filter = ("activity_type", "timestamp")
    search_fields = ("participant__email", "description")
    readonly_fields = (
        "participant",
        "activity_type",
        "description",
        "timestamp",
        "metadata",
    )


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("participant", "balance", "currency", "status", "created_at")
    list_filter = ("currency", "status", "created_at")
    search_fields = ("participant__email", "participant__full_name")
    readonly_fields = ("id", "created_at")

    fieldsets = (
        ("Wallet Owner", {"fields": ("participant",)}),
        ("Balance Information", {"fields": ("balance", "currency", "status")}),
        ("Timestamps", {"fields": ("id", "created_at")}),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_ref",
        "wallet",
        "transaction_type",
        "amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = (
        "transaction_type",
        "status",
        "currency",
        "payment_method",
        "created_at",
    )
    search_fields = (
        "transaction_ref",
        "wallet__participant__email",
        "description",
        "recipient__email",
        "sender__email",
    )
    readonly_fields = (
        "id",
        "transaction_ref",
        "created_at",
        "balance_before",
        "balance_after",
    )
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Transaction Details",
            {
                "fields": (
                    "transaction_ref",
                    "wallet",
                    "transaction_type",
                    "amount",
                    "currency",
                )
            },
        ),
        (
            "Payment Information",
            {"fields": ("payment_method", "status", "description")},
        ),
        ("Parties Involved", {"fields": ("recipient", "sender")}),
        ("Balance Tracking", {"fields": ("balance_before", "balance_after")}),
        ("Additional Data", {"fields": ("metadata",)}),
        ("Timestamps", {"fields": ("id", "created_at")}),
    )


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "amount",
        "currency",
        "status",
        "request_type",
        "created_at",
        "admin_reviewer",
    )
    list_filter = ("status", "request_type", "currency", "created_at")
    search_fields = ("provider__email", "provider__full_name", "reason", "admin_notes")
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Request Information",
            {
                "fields": (
                    "provider",
                    "request_type",
                    "amount",
                    "currency",
                    "reason",
                    "status",
                )
            },
        ),
        ("Related Transactions", {"fields": ("transaction", "refund_transaction")}),
        ("Admin Review", {"fields": ("admin_reviewer", "admin_notes", "reviewed_at")}),
        ("Timestamps", {"fields": ("id", "created_at", "updated_at")}),
    )


@admin.register(FeatureFlagConfig)
class FeatureFlagConfigAdmin(admin.ModelAdmin):
    list_display = (
        "flag_name",
        "is_enabled",
        "is_active",
        "rollout_percentage",
        "enabled_regions_display",
        "updated_at",
    )
    list_filter = ("is_enabled", "is_active", "created_at")
    search_fields = ("flag_name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "created_at"
    
    fieldsets = (
        (
            "Flag Information",
            {
                "fields": (
                    "flag_name",
                    "description",
                    "is_enabled",
                    "is_active",
                )
            },
        ),
        (
            "Targeting",
            {
                "fields": (
                    "enabled_regions",
                    "rollout_percentage",
                    "allowed_roles",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
    
    def enabled_regions_display(self, obj):
        """Display enabled regions in a readable format."""
        if not obj.enabled_regions:
            return "All regions"
        regions = obj.enabled_regions.split(',')
        return ", ".join(regions[:3]) + ("..." if len(regions) > 3 else "")
    enabled_regions_display.short_description = "Regions"


@admin.register(RegionalConfiguration)
class RegionalConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "region_name",
        "region_code",
        "domain",
        "country_code",
        "payment_provider",
        "is_active",
        "maintenance_mode",
    )
    list_filter = ("is_active", "maintenance_mode", "payment_provider", "country_code")
    search_fields = ("region_name", "region_code", "domain")
    readonly_fields = ("id", "created_at", "updated_at")
    
    fieldsets = (
        (
            "Region Information",
            {
                "fields": (
                    "region_code",
                    "region_name",
                    "domain",
                    "country_code",
                )
            },
        ),
        (
            "Localization",
            {
                "fields": (
                    "region_timezone",
                    "language_code",
                    "currency_code",
                )
            },
        ),
        (
            "Payment Configuration",
            {
                "fields": (
                    "payment_provider",
                    "payment_api_key_encrypted",
                    "payment_webhook_secret",
                )
            },
        ),
        (
            "Service Limits",
            {
                "fields": (
                    "max_appointment_distance_km",
                    "max_delivery_distance_km",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "is_active",
                    "maintenance_mode",
                    "maintenance_message",
                )
            },
        ),
        (
            "Database Info",
            {
                "fields": (
                    "database_host",
                    "database_name",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


# Register SystemConfiguration
from .system_config import SystemConfiguration

@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ('id', 'default_consultation_fee', 'default_consultation_currency', 'platform_fee_percentage', 'tax_percentage', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Consultation Fee', {
            'fields': ('default_consultation_fee', 'default_consultation_currency')
        }),
        ('Fee Structure', {
            'fields': ('platform_fee_percentage', 'tax_percentage', 'wallet_topup_fee_percentage')
        }),
        ('Status', {
            'fields': ('is_active', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ParticipantPreferences)
class ParticipantPreferencesAdmin(admin.ModelAdmin):
    list_display = (
        'participant_email',
        'theme',
        'language',
        'enable_email_notifications',
        'enable_sms_notifications',
        'updated_at',
    )
    list_filter = (
        'theme',
        'language',
        'enable_email_notifications',
        'enable_sms_notifications',
        'enable_push_notifications',
        'enable_two_factor_auth',
    )
    search_fields = ('participant__email', 'participant__full_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'updated_at'
    
    fieldsets = (
        ('Participant', {
            'fields': ('participant',)
        }),
        ('Appearance', {
            'fields': ('theme', 'font_size', 'language')
        }),
        ('Notification Channels', {
            'fields': (
                'enable_push_notifications',
                'enable_email_notifications',
                'enable_sms_notifications',
            )
        }),
        ('Notification Types', {
            'fields': (
                'notify_appointment_confirmed',
                'notify_appointment_cancelled',
                'notify_appointment_reminder',
                'notify_prescription_ready',
                'notify_test_results',
                'notify_payment_received',
                'notify_payment_due',
                'notify_new_message',
                'notify_marketing',
            ),
            'classes': ('collapse',),
        }),
        ('Reminders', {
            'fields': ('appointment_reminder_time',)
        }),
        ('Privacy & Security', {
            'fields': (
                'enable_two_factor_auth',
                'profile_visible_to_providers',
                'allow_anonymous_data_sharing',
            )
        }),
        ('Data & Storage', {
            'fields': ('enable_auto_backup',)
        }),
        ('Medical Info', {
            'fields': ('blood_type',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at')
        }),
    )
    
    def participant_email(self, obj):
        return obj.participant.email
    participant_email.short_description = 'Participant'
    participant_email.admin_order_field = 'participant__email'


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = (
        'participant_email',
        'full_name',
        'relationship',
        'phone_number',
        'is_primary',
        'created_at',
    )
    list_filter = ('relationship', 'is_primary', 'created_at')
    search_fields = (
        'participant__email',
        'participant__full_name',
        'full_name',
        'phone_number',
        'email',
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Participant', {
            'fields': ('participant',)
        }),
        ('Contact Information', {
            'fields': (
                'full_name',
                'relationship',
                'phone_number',
                'email',
                'is_primary',
            )
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at')
        }),
    )
    
    def participant_email(self, obj):
        return obj.participant.email
    participant_email.short_description = 'Participant'
    participant_email.admin_order_field = 'participant__email'


@admin.register(LegalRepresentative)
class LegalRepresentativeAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'participant_name',
        'position_display',
        'email',
        'is_verified',
        'created_at',
    )
    list_filter = ('position', 'id_type', 'is_verified', 'created_at')
    search_fields = (
        'full_name',
        'email',
        'phone_number',
        'id_number',
        'participant__email',
        'participant__full_name',
    )
    readonly_fields = ('id', 'created_at', 'updated_at', 'verified_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Organization', {
            'fields': ('participant',)
        }),
        ('Personal Information', {
            'fields': ('full_name', 'email', 'phone_number')
        }),
        ('Position', {
            'fields': ('position', 'position_other', 'date_of_appointment', 'authorization_scope')
        }),
        ('Identification', {
            'fields': ('id_type', 'id_number', 'id_expiry_date')
        }),
        ('Documents', {
            'fields': ('id_document_front', 'id_document_back', 'proof_of_position')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_by', 'verified_at'),
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at')
        }),
    )
    
    def participant_name(self, obj):
        return obj.participant.full_name
    participant_name.short_description = 'Organization'
    participant_name.admin_order_field = 'participant__full_name'
    
    def position_display(self, obj):
        return obj.get_position_display_full()
    position_display.short_description = 'Position'
    
    def save_model(self, request, obj, form, change):
        if 'is_verified' in form.changed_data and obj.is_verified:
            obj.verified_by = request.user
            from django.utils import timezone
            obj.verified_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(HospitalStaffAffiliation)
class HospitalStaffAffiliationAdmin(admin.ModelAdmin):
    list_display = (
        'doctor_name',
        'hospital_name',
        'affiliation_type',
        'status',
        'can_manage_own_payments',
        'can_manage_own_claims',
        'created_at',
    )
    list_filter = ('affiliation_type', 'status', 'created_at')
    search_fields = (
        'doctor__full_name',
        'doctor__email',
        'hospital__full_name',
        'hospital__email',
        'job_title',
        'department',
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Affiliation', {
            'fields': ('doctor', 'hospital', 'affiliation_type', 'status')
        }),
        ('Employment Details', {
            'fields': ('employment_start_date', 'employment_end_date', 'job_title', 'department')
        }),
        ('Permissions', {
            'fields': ('can_manage_own_payments', 'can_manage_own_claims')
        }),
        ('Contract', {
            'fields': ('contract_document', 'notes')
        }),
        ('Metadata', {
            'fields': ('id', 'created_by', 'created_at', 'updated_at')
        }),
    )

    def doctor_name(self, obj):
        return f"Dr. {obj.doctor.full_name}"
    doctor_name.short_description = 'Doctor'
    doctor_name.admin_order_field = 'doctor__full_name'

    def hospital_name(self, obj):
        return obj.hospital.full_name
    hospital_name.short_description = 'Hospital'
    hospital_name.admin_order_field = 'hospital__full_name'


@admin.register(StaffPermission)
class StaffPermissionAdmin(admin.ModelAdmin):
    list_display = (
        'doctor_name',
        'hospital_name',
        'permission_display',
        'granted',
        'granted_at',
    )
    list_filter = ('permission', 'granted', 'granted_at')
    search_fields = (
        'affiliation__doctor__full_name',
        'affiliation__hospital__full_name',
    )
    readonly_fields = ('id', 'granted_at')
    date_hierarchy = 'granted_at'

    fieldsets = (
        ('Affiliation', {
            'fields': ('affiliation',)
        }),
        ('Permission', {
            'fields': ('permission', 'granted')
        }),
        ('Metadata', {
            'fields': ('id', 'granted_by', 'granted_at')
        }),
    )

    def doctor_name(self, obj):
        return f"Dr. {obj.affiliation.doctor.full_name}"
    doctor_name.short_description = 'Doctor'
    doctor_name.admin_order_field = 'affiliation__doctor__full_name'

    def hospital_name(self, obj):
        return obj.affiliation.hospital.full_name
    hospital_name.short_description = 'Hospital'
    hospital_name.admin_order_field = 'affiliation__hospital__full_name'

    def permission_display(self, obj):
        return obj.get_permission_display()
    permission_display.short_description = 'Permission'
    permission_display.admin_order_field = 'permission'
