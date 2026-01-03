"""
Sentry middleware for automatic context enrichment
"""
import sentry_sdk
from django.utils.deprecation import MiddlewareMixin


class SentryContextMiddleware(MiddlewareMixin):
    """Automatically enrich Sentry events with request context"""
    
    def process_request(self, request):
        """Add request context to Sentry"""
        if hasattr(request, 'participant') and request.participant:
            participant = request.participant
            sentry_sdk.set_user({
                "id": str(participant.uid),
                "username": getattr(participant, 'username', None),
                "email": getattr(participant, 'email', None),
                "role": getattr(participant, 'role', None),
            })
        
        sentry_sdk.set_context("request_info", {
            "path": request.path,
            "method": request.method,
            "query_params": dict(request.GET),
        })
        
        return None
    
    def process_response(self, request, response):
        """Add response context to Sentry"""
        sentry_sdk.set_context("response_info", {
            "status_code": response.status_code,
        })
        return response
    
    def process_exception(self, request, exception):
        """Capture exceptions with full context"""
        sentry_sdk.set_context("error_context", {
            "path": request.path,
            "method": request.method,
            "participant_id": str(request.participant.uid) if hasattr(request, 'participant') and request.participant else None,
        })
        
        sentry_sdk.capture_exception(exception)
        return None
