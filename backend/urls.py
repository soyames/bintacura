from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView, RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from . import views
from communication.views import notifications_list_view, messages_list_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", views.health_check, name="health_check"),
    path("health-check", views.health_check, name="health_check_render"),
    path("api/health/", views.health_check, name="api_health_check"),
    path("set-language/", views.set_language, name="set_language"),
    path("superadmin/", include("core.admin_urls")),
    path("super-admin/", include("super_admin.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/v1/", views.api_root, name="api_root"),
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path(
        "api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"
    ),
    path("api/v1/core/", include("core.urls")),
    path(
        "api/v1/auth/",
        include(("authentication.urls", "auth_api"), namespace="auth_api"),
    ),
    path("api/v1/doctor/", include("doctor.api_urls")),
    path("api/v1/patient/", include("patient.api_urls")),
    path("api/v1/appointments/", include("appointments.urls")),
    path("api/v1/prescriptions/", include("prescriptions.urls")),
    path("api/v1/payments/", include("payments.urls")),
    path(
        "api/v1/insurance/",
        include(("insurance.urls", "insurance_api"), namespace="insurance_api"),
    ),
    path("api/v1/health-records/", include("health_records.urls")),
    path("api/v1/communication/", include("communication.urls")),
    path("api/v1/ai/", include("ai.urls")),
    path("api/v1/analytics/", include("analytics.urls")),
    path("api/v1/ads/", include("ads.urls")),
    path("api/v1/qrcode/", include("qrcode_generator.urls")),
    path("api/v1/pharmacy/", include("pharmacy.urls")),
    path("api/v1/hospital/", include("hospital.urls")),
    path("api/v1/transport/", include("transport.urls")),
    path("api/v1/currency/", include("currency_converter.urls")),
    path("api/v1/preferences/", include("core.preferences_urls")),
    path("api/v1/sync/", include("sync.urls")),  # Offline-first sync endpoints
    path("api/v1/financial/", include(("financial.urls", "financial"), namespace="financial")),
    path("api/v1/hr/", include(("hr.urls", "hr"), namespace="hr")),
    path("api/v1/menstruation/", include("menstruation.api_urls")),  # Menstruation tracker API
    path("account/", include("core.account_urls")),
    path("survey/", include(("analytics.survey_urls", "analytics"), namespace="analytics_survey")),
    path("", include("queue_management.urls")),
    path("api/v1/monitoring/", include("core.monitoring_urls")),
    path("", TemplateView.as_view(template_name="main_landing.html"), name="home"),
    path("auth/", include(("authentication.urls", "auth_web"), namespace="auth_web")),
    path("logout/", RedirectView.as_view(url="/auth/logout/", permanent=False)),
    path(
        "info/about/",
        TemplateView.as_view(template_name="info/about.html"),
        name="about",
    ),
    path(
        "info/services/",
        TemplateView.as_view(template_name="info/services.html"),
        name="services",
    ),
    path(
        "info/privacy/",
        TemplateView.as_view(template_name="info/privacy.html"),
        name="privacy",
    ),
    path(
        "info/terms/",
        TemplateView.as_view(template_name="info/terms.html"),
        name="terms",
    ),
    path(
        "info/contact/",
        TemplateView.as_view(template_name="info/contact.html"),
        name="contact",
    ),
    path(
        "info/help/", TemplateView.as_view(template_name="info/help.html"), name="help"
    ),
    path("info/faq/", TemplateView.as_view(template_name="info/help.html"), name="faq"),
    path("patient/", include("patient.urls")),
    path("patient/menstruation/", include("menstruation.urls")),  # Menstruation tracker web views
    path("doctor/", include("doctor.urls")),
    path("hospital/", include("hospital.web_urls")),
    path("notifications/", notifications_list_view, name='notifications'),
    path("messages/", messages_list_view, name='messages'),
    path("pharmacy/", include("pharmacy.web_urls")),
    path("insurance/", include("insurance.web_urls")),
    path("dashboard/", include("core.dashboard_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = "BintaCura Administration"
admin.site.site_title = "BintaCura Admin Portal"
admin.site.index_title = "Welcome to BintaCura Admin Portal"

