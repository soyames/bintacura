from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'rates', views.ExchangeRateViewSet, basename='exchange-rate')
router.register(r'pairs', views.CurrencyPairViewSet, basename='currency-pair')
router.register(r'conversion', views.CurrencyConversionViewSet, basename='conversion')

urlpatterns = [
    path('', include(router.urls)),
]
