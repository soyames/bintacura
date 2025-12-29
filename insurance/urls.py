from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "insurance"

router = DefaultRouter()
router.register(r"packages", views.InsurancePackageViewSet, basename="package")
router.register(
    r"subscriptions", views.InsuranceSubscriptionViewSet, basename="subscription"
)
router.register(r"invoices", views.InsuranceInvoiceViewSet, basename="invoice")
router.register(r"claims", views.InsuranceClaimViewSet, basename="claim")
router.register(r"enquiries", views.InsuranceCoverageEnquiryViewSet, basename="enquiry")
router.register(r"staff", views.InsuranceStaffViewSet, basename="staff")
router.register(r"network", views.HealthcarePartnerNetworkViewSet, basename="network")

urlpatterns = [
    path("", include(router.urls)),
]
