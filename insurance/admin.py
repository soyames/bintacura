from django.contrib import admin
from .models import (
    InsurancePackage, PatientInsuranceCard, InsuranceClaim, EnrollmentRequest,
    ServiceCategory, CoverageRule, CopayDeductibleConfig, FeeSchedule,
    ClaimAdjudicationRule, ClaimAdjudicationResult, MedicalNecessityReview,
    ProviderCredential, ProviderContract, ProviderPerformance,
    UnderwritingApplication, RiskAssessment, MembershipRenewal, GracePeriod, FraudAlert
)

@admin.register(InsurancePackage)
class InsurancePackageAdmin(admin.ModelAdmin):  # Admin configuration for InsurancePackage model
    list_display = ('id', 'company', 'name', 'is_active', 'consultation_discount_percentage', 'is_consultation_free', 'created_at')
    list_filter = ('is_active', 'is_consultation_free')
    search_fields = ('name', 'company__email')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(PatientInsuranceCard)
class PatientInsuranceCardAdmin(admin.ModelAdmin):  # Admin configuration for PatientInsuranceCard model
    list_display = ('id', 'patient', 'insurance_package', 'card_number', 'status', 'issue_date', 'expiry_date')
    list_filter = ('status',)
    search_fields = ('card_number', 'policy_number', 'patient__email')
    date_hierarchy = 'issue_date'

@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(admin.ModelAdmin):  # Admin configuration for InsuranceClaim model
    list_display = ('id', 'claim_number', 'patient', 'service_type', 'claimed_amount', 'approved_amount', 'status', 'submission_date')
    list_filter = ('status', 'service_type')
    search_fields = ('claim_number', 'patient__email')
    date_hierarchy = 'submission_date'
    readonly_fields = ('created_at', 'updated_at')

@admin.register(EnrollmentRequest)
class EnrollmentRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'insurance_package', 'status', 'requested_coverage_start', 'created_at')
    list_filter = ('status',)
    search_fields = ('patient__email',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('category_code', 'category_name', 'insurance_company', 'parent_category', 'is_active')
    list_filter = ('insurance_company', 'is_active')
    search_fields = ('category_code', 'category_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CoverageRule)
class CoverageRuleAdmin(admin.ModelAdmin):
    list_display = ('insurance_package', 'service_category', 'coverage_percentage', 'max_coverage_per_service', 'is_active', 'effective_date')
    list_filter = ('insurance_package', 'is_active', 'requires_pre_authorization', 'is_excluded')
    search_fields = ('service_category__category_name',)
    date_hierarchy = 'effective_date'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(CopayDeductibleConfig)
class CopayDeductibleConfigAdmin(admin.ModelAdmin):
    list_display = ('insurance_package', 'annual_deductible', 'out_of_pocket_maximum', 'coinsurance_percentage', 'effective_date')
    list_filter = ('insurance_package', 'effective_date')
    search_fields = ('insurance_package__name',)
    date_hierarchy = 'effective_date'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FeeSchedule)
class FeeScheduleAdmin(admin.ModelAdmin):
    list_display = ('service_code', 'service_description', 'service_category', 'maximum_allowed_amount', 'contracted_rate', 'is_active', 'effective_date')
    list_filter = ('insurance_company', 'service_category', 'is_active')
    search_fields = ('service_code', 'service_description')
    date_hierarchy = 'effective_date'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ClaimAdjudicationRule)
class ClaimAdjudicationRuleAdmin(admin.ModelAdmin):
    list_display = ('rule_code', 'rule_name', 'rule_type', 'priority_order', 'is_active')
    list_filter = ('insurance_company', 'rule_type', 'is_active')
    search_fields = ('rule_code', 'rule_name')
    ordering = ('priority_order',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ClaimAdjudicationResult)
class ClaimAdjudicationResultAdmin(admin.ModelAdmin):
    list_display = ('claim', 'adjudication_status', 'total_billed_amount', 'allowed_amount', 'insurance_pays', 'patient_responsibility', 'adjudication_date')
    list_filter = ('adjudication_status', 'requires_medical_review', 'requires_fraud_review')
    search_fields = ('claim__claim_number',)
    date_hierarchy = 'adjudication_date'
    readonly_fields = ('created_at',)


@admin.register(MedicalNecessityReview)
class MedicalNecessityReviewAdmin(admin.ModelAdmin):
    list_display = ('claim', 'review_status', 'reviewer', 'review_date', 'peer_review_required')
    list_filter = ('review_status', 'peer_review_required')
    search_fields = ('claim__claim_number', 'diagnosis_code', 'procedure_code')
    date_hierarchy = 'review_date'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProviderCredential)
class ProviderCredentialAdmin(admin.ModelAdmin):
    list_display = ('credential_number', 'provider', 'insurance_company', 'status', 'application_date', 'approval_date', 'expiration_date')
    list_filter = ('insurance_company', 'status', 'license_verified', 'board_cert_verified')
    search_fields = ('credential_number', 'provider__full_name', 'license_number')
    date_hierarchy = 'application_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {'fields': ('credential_number', 'insurance_company', 'provider', 'status')}),
        ('Dates', {'fields': ('application_date', 'approval_date', 'expiration_date', 'recredentialing_due_date')}),
        ('License Verification', {'fields': ('license_number', 'license_verified', 'license_verification_date')}),
        ('Certifications', {'fields': ('board_certification', 'board_cert_verified', 'malpractice_insurance', 'malpractice_verified')}),
        ('Other Credentials', {'fields': ('dea_number', 'npi_number', 'education_credentials', 'hospital_affiliations')}),
        ('Verification Status', {'fields': ('references_checked', 'background_check_completed', 'credentialing_committee_approved', 'committee_approval_date')}),
        ('Outcome', {'fields': ('denial_reason', 'verified_by', 'notes')}),
    )


@admin.register(ProviderContract)
class ProviderContractAdmin(admin.ModelAdmin):
    list_display = ('contract_number', 'provider', 'insurance_company', 'contract_type', 'status', 'effective_date', 'termination_date')
    list_filter = ('insurance_company', 'contract_type', 'status', 'auto_renew')
    search_fields = ('contract_number', 'provider__full_name')
    date_hierarchy = 'effective_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {'fields': ('contract_number', 'insurance_company', 'provider', 'contract_type', 'status')}),
        ('Contract Period', {'fields': ('effective_date', 'termination_date', 'auto_renew', 'renewal_notice_days')}),
        ('Payment Terms', {'fields': ('payment_terms', 'reimbursement_rates', 'capitation_amount_per_member')}),
        ('Coverage', {'fields': ('services_covered', 'quality_metrics', 'performance_bonus_structure', 'claim_submission_deadline_days')}),
        ('Requirements', {'fields': ('credentialing_requirements', 'termination_clause', 'dispute_resolution_process')}),
        ('Signatures', {'fields': ('signed_by_provider', 'provider_signature_date', 'signed_by_insurance', 'insurance_signature_date')}),
        ('Document', {'fields': ('contract_document_url', 'notes')}),
    )


@admin.register(ProviderPerformance)
class ProviderPerformanceAdmin(admin.ModelAdmin):
    list_display = ('provider', 'measurement_period_start', 'measurement_period_end', 'total_claims_submitted', 'claims_denial_rate', 'quality_score', 'performance_tier')
    list_filter = ('insurance_company', 'performance_tier', 'outlier_flag')
    search_fields = ('provider__full_name',)
    date_hierarchy = 'measurement_period_end'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UnderwritingApplication)
class UnderwritingApplicationAdmin(admin.ModelAdmin):
    list_display = ('application_number', 'enrollment_request', 'status', 'submission_date', 'underwriter_assigned', 'risk_score', 'premium_rating_multiplier')
    list_filter = ('status', 'medical_exam_required', 'medical_exam_completed')
    search_fields = ('application_number', 'enrollment_request__patient__full_name')
    date_hierarchy = 'submission_date'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ('underwriting_application', 'risk_level', 'total_risk_score', 'smoking_status', 'assessment_date', 'assessed_by')
    list_filter = ('risk_level', 'smoking_status')
    search_fields = ('underwriting_application__application_number',)
    date_hierarchy = 'assessment_date'
    readonly_fields = ('created_at',)


@admin.register(MembershipRenewal)
class MembershipRenewalAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'renewal_date', 'renewal_premium', 'status', 'auto_renewed', 'payment_received_date')
    list_filter = ('status', 'auto_renewed')
    search_fields = ('subscription__patient__full_name',)
    date_hierarchy = 'renewal_date'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(GracePeriod)
class GracePeriodAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'original_due_date', 'grace_period_end', 'amount_due', 'late_fee', 'status', 'reminder_sent_count')
    list_filter = ('status', 'payment_received', 'coverage_suspended_during_grace')
    search_fields = ('subscription__patient__full_name',)
    date_hierarchy = 'grace_period_end'
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FraudAlert)
class FraudAlertAdmin(admin.ModelAdmin):
    list_display = ('alert_number', 'alert_type', 'severity', 'status', 'detection_date', 'risk_score', 'potential_loss_amount', 'assigned_investigator')
    list_filter = ('insurance_company', 'alert_type', 'severity', 'status', 'law_enforcement_notified')
    search_fields = ('alert_number', 'provider__full_name', 'member__full_name')
    date_hierarchy = 'detection_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Alert Information', {'fields': ('alert_number', 'insurance_company', 'alert_type', 'severity', 'status', 'detection_date')}),
        ('Related Entities', {'fields': ('claim', 'provider', 'member')}),
        ('Detection', {'fields': ('pattern_description', 'evidence_data', 'risk_score', 'potential_loss_amount', 'related_claims')}),
        ('Investigation', {'fields': ('assigned_investigator', 'investigation_notes', 'investigation_start_date', 'investigation_end_date')}),
        ('Outcome', {'fields': ('outcome', 'action_taken', 'recovery_amount')}),
        ('Law Enforcement', {'fields': ('law_enforcement_notified', 'law_enforcement_case_number')}),
    )
