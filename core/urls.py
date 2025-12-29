from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .system_views import GetConsultationFeeView, GetParticipantServicesView, ConvertCurrencyView

app_name = "core"

router = DefaultRouter()
router.register(r"participants", views.ParticipantViewSet, basename="participant")
router.register(r"profiles", views.ParticipantProfileViewSet, basename="participant-profile")
router.register(r"wallets", views.WalletViewSet, basename="wallet")
router.register(r"transactions", views.TransactionViewSet, basename="transaction")
router.register(r"security", views.AntiScrapingMonitorViewSet, basename="security")
router.register(
    r"security-monitor", views.SecurityMonitorViewSet, basename="security-monitor"
)

urlpatterns = [
    path("", include(router.urls)),

    path("system/consultation-fee/", GetConsultationFeeView.as_view(), name="consultation-fee"),
    path("system/convert-currency/", ConvertCurrencyView.as_view(), name="convert-currency"),
    path("participants/<uuid:participant_id>/services/", GetParticipantServicesView.as_view(), name="participant-services"),
    path("contact/", views.ContactFormAPIView.as_view(), name="contact-form"),
]
