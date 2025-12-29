from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import AllowAny
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import sys


class LandingPageView(TemplateView):
    template_name = "main_landing.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_superuser or (hasattr(request.user, "role") and request.user.role == "super_admin"):
                return redirect("/superadmin/dashboard/")

            role_map = {
                "patient": "/patient/dashboard/",
                "doctor": "/doctor/dashboard/",
                "hospital": "/hospital/dashboard/",
                "pharmacy": "/pharmacy/dashboard/",
                "insurance": "/insurance/dashboard/",
                "insurance_company": "/insurance/dashboard/",
                "lab": "/hospital/dashboard/",
                "admin": "/superadmin/dashboard/",
            }

            user_role = (
                request.user.role.lower()
                if hasattr(request.user, "role") and request.user.role
                else "patient"
            )
            return redirect(role_map.get(user_role, "/patient/dashboard/"))

        return super().get(request, *args, **kwargs)


@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "auth": {
                "token": reverse("token_obtain_pair", request=request, format=format),
                "token_refresh": reverse(
                    "token_refresh", request=request, format=format
                ),
            },
            "endpoints": {
                "core": request.build_absolute_uri("/api/core/"),
                "authentication": request.build_absolute_uri("/api/auth/"),
                "appointments": request.build_absolute_uri("/api/appointments/"),
                "prescriptions": request.build_absolute_uri("/api/prescriptions/"),
                "payments": request.build_absolute_uri("/api/payments/"),
                "insurance": request.build_absolute_uri("/api/insurance/"),
                "health_records": request.build_absolute_uri("/api/health-records/"),
                "communication": request.build_absolute_uri("/api/communication/"),
                "providers": request.build_absolute_uri("/api/providers/"),
                "analytics": request.build_absolute_uri("/api/analytics/"),
            },
            "admin": request.build_absolute_uri("/admin/"),
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    health_status = {
        "status": "healthy",
        "python_version": sys.version,
    }

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"
        return JsonResponse(health_status, status=503)

    return JsonResponse(health_status)


@login_required
@require_POST
def set_language(request):
    language_code = request.POST.get('language', 'fr')
    if language_code in ['fr', 'en']:
        request.user.preferred_language = language_code
        request.user.save(update_fields=['preferred_language'])
        return JsonResponse({'status': 'success', 'language': language_code})
    return JsonResponse({'status': 'error', 'message': 'Invalid language'}, status=400)
