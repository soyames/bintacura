from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .system_views import GetConsultationFeeView, GetParticipantServicesView, ConvertCurrencyView
from .map_views import map_search_view, map_search_api

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
    path("price-comparison/", views.PriceComparisonView.as_view(), name="price-comparison"),
    path("api/price-comparison/", views.PriceComparisonAPIView.as_view(), name="api-price-comparison"),
    path("map-search/", map_search_view, name="map-search"),
    path("api/map-search/", map_search_api, name="api-map-search"),
]
