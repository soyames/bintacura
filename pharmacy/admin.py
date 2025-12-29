from django.contrib import admin
from .models import (
    PharmacyInventory, PharmacyOrder, PharmacyOrderItem,
    PharmacySupplier, PharmacyPurchase, PharmacyPurchaseItem,
    PharmacySale, PharmacySaleItem, PharmacyStaff,
    DoctorPharmacyReferral, PharmacyBonusConfig,
    PharmacyCounter, OrderQueue, DeliveryTracking, PickupVerification
)

@admin.register(PharmacyInventory)
class PharmacyInventoryAdmin(admin.ModelAdmin):  # Admin configuration for PharmacyInventory model
    list_display = ['medication', 'pharmacy', 'batch_number', 'quantity_in_stock', 'expiry_date']
    list_filter = ['pharmacy', 'expiry_date']
    search_fields = ['medication__name', 'batch_number']

@admin.register(PharmacyOrder)
class PharmacyOrderAdmin(admin.ModelAdmin):  # Admin configuration for PharmacyOrder model
    list_display = ['order_number', 'pharmacy', 'patient', 'status', 'total_amount', 'order_date']
    list_filter = ['status', 'pharmacy', 'order_date']
    search_fields = ['order_number', 'patient__email']

@admin.register(PharmacySupplier)
class PharmacySupplierAdmin(admin.ModelAdmin):  # Admin configuration for PharmacySupplier model
    list_display = ['name', 'pharmacy', 'email', 'phone_number', 'is_active']
    list_filter = ['pharmacy', 'is_active']
    search_fields = ['name', 'email']

@admin.register(PharmacyPurchase)
class PharmacyPurchaseAdmin(admin.ModelAdmin):  # Admin configuration for PharmacyPurchase model
    list_display = ['purchase_number', 'pharmacy', 'supplier', 'status', 'total_amount', 'order_date']
    list_filter = ['status', 'pharmacy', 'order_date']
    search_fields = ['purchase_number']

@admin.register(PharmacySale)
class PharmacySaleAdmin(admin.ModelAdmin):  # Admin configuration for PharmacySale model
    list_display = ['sale_number', 'pharmacy', 'patient', 'final_amount', 'payment_method', 'sale_date']
    list_filter = ['pharmacy', 'payment_method', 'sale_date']
    search_fields = ['sale_number', 'patient__email']

@admin.register(PharmacyStaff)
class PharmacyStaffAdmin(admin.ModelAdmin):  # Admin configuration for PharmacyStaff model
    list_display = ['full_name', 'pharmacy', 'role', 'email', 'is_active', 'hire_date']
    list_filter = ['pharmacy', 'role', 'is_active']
    search_fields = ['full_name', 'email']

@admin.register(DoctorPharmacyReferral)
class DoctorPharmacyReferralAdmin(admin.ModelAdmin):  # Admin configuration for DoctorPharmacyReferral model
    list_display = ['doctor', 'pharmacy', 'patient', 'referral_date', 'was_fulfilled', 'bonus_earned', 'bonus_paid']
    list_filter = ['pharmacy', 'was_fulfilled', 'bonus_paid', 'referral_date']
    search_fields = ['doctor__email', 'patient__email']

@admin.register(PharmacyBonusConfig)
class PharmacyBonusConfigAdmin(admin.ModelAdmin):  # Admin configuration for PharmacyBonusConfig model
    list_display = ['pharmacy', 'doctor', 'bonus_type', 'bonus_percentage', 'is_active']
    list_filter = ['pharmacy', 'bonus_type', 'is_active']


@admin.register(PharmacyCounter)
class PharmacyCounterAdmin(admin.ModelAdmin):
    list_display = ['counter_number', 'counter_name', 'pharmacy', 'is_active', 'current_staff', 'current_session_started']
    list_filter = ['pharmacy', 'is_active']
    search_fields = ['counter_number', 'counter_name']


@admin.register(OrderQueue)
class OrderQueueAdmin(admin.ModelAdmin):
    list_display = ['queue_number', 'order', 'pharmacy', 'status', 'priority', 'claimed_by', 'counter', 'created_at']
    list_filter = ['pharmacy', 'status', 'priority']
    search_fields = ['queue_number', 'order__order_number', 'qr_code']
    readonly_fields = ['qr_code']


@admin.register(DeliveryTracking)
class DeliveryTrackingAdmin(admin.ModelAdmin):
    list_display = ['tracking_number', 'order', 'pharmacy', 'status', 'delivery_person', 'estimated_delivery_time', 'confirmed_by_patient']
    list_filter = ['pharmacy', 'status', 'confirmed_by_patient']
    search_fields = ['tracking_number', 'order__order_number']
    readonly_fields = ['tracking_number', 'patient_confirmation_code']


@admin.register(PickupVerification)
class PickupVerificationAdmin(admin.ModelAdmin):
    list_display = ['order', 'pharmacy', 'scanned_by', 'scanned_at', 'counter', 'payment_completed']
    list_filter = ['pharmacy', 'payment_completed', 'scanned_at']
    search_fields = ['qr_code', 'verification_code', 'order__order_number']
    readonly_fields = ['qr_code', 'verification_code']
