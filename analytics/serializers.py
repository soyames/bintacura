from rest_framework import serializers
from .models import PlatformStatistics, UserGrowthMetrics, RevenueMetrics


class PlatformStatisticsSerializer(serializers.ModelSerializer):  # Serializer for platform-wide statistics data
    class Meta:  # Meta class implementation
        model = PlatformStatistics
        fields = "__all__"


class UserGrowthMetricsSerializer(serializers.ModelSerializer):  # Serializer for user growth metrics by role
    class Meta:  # Meta class implementation
        model = UserGrowthMetrics
        fields = "__all__"


class RevenueMetricsSerializer(serializers.ModelSerializer):  # Serializer for daily revenue and transaction metrics
    class Meta:  # Meta class implementation
        model = RevenueMetrics
        fields = "__all__"


class DashboardOverviewSerializer(serializers.Serializer):  # Serializer for admin dashboard overview statistics
    total_users = serializers.IntegerField()
    total_patients = serializers.IntegerField()
    total_doctors = serializers.IntegerField()
    total_hospitals = serializers.IntegerField()
    total_pharmacies = serializers.IntegerField()
    total_insurance = serializers.IntegerField()
    new_users_today = serializers.IntegerField()
    total_transactions = serializers.IntegerField()
    transaction_volume = serializers.FloatField()
    platform_fees = serializers.FloatField()
    pending_verifications = serializers.IntegerField()
    verified_providers = serializers.IntegerField()
    pending_refunds = serializers.IntegerField()
    total_refund_requests = serializers.IntegerField()
    total_appointments = serializers.IntegerField()
    today_appointments = serializers.IntegerField()


class UserGrowthDataSerializer(serializers.Serializer):  # Serializer for user growth data over time
    date = serializers.CharField()
    new_users = serializers.IntegerField()
    total_users = serializers.IntegerField()


class RevenueDataSerializer(serializers.Serializer):  # Serializer for revenue data over time
    date = serializers.CharField()
    revenue = serializers.FloatField()
    fees = serializers.FloatField()


class RoleDistributionSerializer(serializers.Serializer):  # Serializer for user role distribution statistics
    role = serializers.CharField()
    count = serializers.IntegerField()


class ActivitySerializer(serializers.Serializer):  # Serializer for recent participant activity data
    participant = serializers.CharField()
    activity_type = serializers.CharField()
    description = serializers.CharField()
    timestamp = serializers.DateTimeField()


class TopProviderSerializer(serializers.Serializer):  # Serializer for top healthcare provider statistics
    name = serializers.CharField()
    role = serializers.CharField()
    email = serializers.EmailField()
    appointments = serializers.IntegerField()


class GeographicDistributionSerializer(serializers.Serializer):  # Serializer for geographic user distribution by city
    city = serializers.CharField()
    count = serializers.IntegerField()


class DoctorAnalyticsSerializer(serializers.Serializer):  # Serializer for doctor-specific analytics and performance metrics
    total_appointments = serializers.IntegerField()
    completed_appointments = serializers.IntegerField()
    cancelled_appointments = serializers.IntegerField()
    pending_appointments = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    total_patients = serializers.IntegerField()
    average_rating = serializers.FloatField()
    completion_rate = serializers.FloatField()


class HospitalAnalyticsSerializer(serializers.Serializer):  # Serializer for hospital-specific analytics and metrics
    total_doctors = serializers.IntegerField()
    total_appointments = serializers.IntegerField()
    total_patients = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    bed_occupancy_rate = serializers.FloatField()
    average_rating = serializers.FloatField()


class PharmacyAnalyticsSerializer(serializers.Serializer):  # Serializer for pharmacy-specific analytics and prescription metrics
    total_prescriptions = serializers.IntegerField()
    fulfilled_prescriptions = serializers.IntegerField()
    pending_prescriptions = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    total_customers = serializers.IntegerField()
    average_order_value = serializers.FloatField()
    fulfillment_rate = serializers.FloatField()


class InsuranceAnalyticsSerializer(serializers.Serializer):  # Serializer for insurance company analytics and claims metrics
    total_claims = serializers.IntegerField()
    approved_claims = serializers.IntegerField()
    pending_claims = serializers.IntegerField()
    rejected_claims = serializers.IntegerField()
    total_claims_amount = serializers.FloatField()
    total_approved_amount = serializers.FloatField()
    approval_rate = serializers.FloatField()
    active_subscriptions = serializers.IntegerField()


class PatientAnalyticsSerializer(serializers.Serializer):  # Serializer for patient-specific analytics and spending metrics
    total_appointments = serializers.IntegerField()
    completed_appointments = serializers.IntegerField()
    total_prescriptions = serializers.IntegerField()
    total_spending = serializers.FloatField()
    wallet_balance = serializers.FloatField()
    insurance_claims = serializers.IntegerField()


class SurveyStatisticsSerializer(serializers.Serializer):  # Serializer for survey response statistics and distributions
    total_responses = serializers.IntegerField()
    sex_distribution = serializers.DictField()
    profession_distribution = serializers.DictField()
    country_distribution = serializers.DictField()
    price_stats = serializers.DictField()
    currency_distribution = serializers.DictField()
    recent_responses = serializers.ListField()
