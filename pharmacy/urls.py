from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import cart_views
from . import payment_views
from . import counter_views

app_name = 'pharmacy_api'

router = DefaultRouter()
router.register(r'inventory', views.PharmacyInventoryViewSet, basename='inventory')
router.register(r'orders', views.PharmacyOrderViewSet, basename='order')
router.register(r'suppliers', views.PharmacySupplierViewSet, basename='supplier')
router.register(r'purchases', views.PharmacyPurchaseViewSet, basename='purchase')
router.register(r'sales', views.PharmacySaleViewSet, basename='sale')
router.register(r'staff', views.PharmacyStaffViewSet, basename='staff')
router.register(r'referrals', views.DoctorPharmacyReferralViewSet, basename='referral')
router.register(r'bonus-configs', views.PharmacyBonusConfigViewSet, basename='bonus-config')
router.register(r'cart', cart_views.ShoppingCartViewSet, basename='cart')
router.register(r'counters', counter_views.PharmacyCounterViewSet, basename='counter')
router.register(r'queue', counter_views.OrderQueueViewSet, basename='queue')
router.register(r'deliveries', counter_views.DeliveryTrackingViewSet, basename='delivery')
router.register(r'pickups', counter_views.PickupVerificationViewSet, basename='pickup')

urlpatterns = [
    path('', include(router.urls)),

    # QR-driven payment endpoints
    path('verify-order/<uuid:order_id>/', payment_views.verify_order_qr, name='verify-order'),
    path('pay-order/<uuid:order_id>/', payment_views.pay_order, name='pay-order'),
    path('scan-order/', payment_views.scan_order_qr, name='scan-order'),
    path('payment-callback/<uuid:order_id>/', payment_views.payment_callback, name='payment-callback'),
    
    # Staff management routes
    path('staff/', views.staff_list, name='staff-list'),
    
    # Counter dashboard routes
    path('staff/counter/', views.counter_dashboard, name='counter-dashboard'),
    path('prescription/search/', views.search_prescription, name='search-prescription'),
    path('prescriptions/<uuid:prescription_id>/prepare/', views.prepare_prescription, name='prepare-prescription'),
    path('payment/<uuid:order_id>/', views.payment_processing, name='payment-processing'),
]
