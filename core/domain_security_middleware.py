from django.http import HttpResponsePermanentRedirect
from django.conf import settings


class DomainSecurityMiddleware:  # Enforces HTTPS and security headers for BINTACURA.bj domain
    def __init__(self, get_response):
        self.get_response = get_response
        self.secure_domains = ['BINTACURA.bj', 'www.BINTACURA.bj']

    def __call__(self, request):
        host = request.get_host().split(':')[0]

        if host in self.secure_domains:
            if not request.is_secure() and not settings.DEBUG:
                url = request.build_absolute_uri(request.get_full_path())
                secure_url = url.replace('http://', 'https://')
                return HttpResponsePermanentRedirect(secure_url)

        response = self.get_response(request)

        if host in self.secure_domains:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response['Permissions-Policy'] = 'geolocation=(self), microphone=(), camera=()'
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https: https://*.tile.openstreetmap.org; "
                "connect-src 'self' https://api.exchangerate-api.com https://nominatim.openstreetmap.org https://router.project-osrm.org; "
                "frame-ancestors 'none';"
            )

        return response

