from django.utils.deprecation import MiddlewareMixin
from core.models import AuditLogEntry
import json


class AuditMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._audit_data = {
            "ip_address": self.get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        }
        return None

    def process_response(self, request, response):
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return response

        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            action_type = self.map_method_to_action(request.method)
            resource_type = self.extract_resource_type(request.path)

            if resource_type:
                try:
                    details = {}
                    if hasattr(request, "body") and request.body:
                        try:
                            details = json.loads(request.body)
                        except:
                            pass

                    AuditLogEntry.objects.create(
                        participant=request.user,
                        action_type=action_type,
                        resource_type=resource_type,
                        resource_id=self.extract_resource_id(request.path),
                        ip_address=request._audit_data.get("ip_address"),
                        user_agent=request._audit_data.get("user_agent"),
                        details=details,
                        success=200 <= response.status_code < 400,
                    )
                except Exception:
                    pass

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def map_method_to_action(self, method):
        mapping = {
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }
        return mapping.get(method, "update")

    def extract_resource_type(self, path):
        parts = path.strip("/").split("/")
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
            return parts[2]
        return None

    def extract_resource_id(self, path):
        parts = path.strip("/").split("/")
        if len(parts) >= 4:
            return parts[3]
        return ""

