from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden, JsonResponse
from django.core.cache import cache
import re
import time
from collections import defaultdict
from .anti_scraping_monitor import AntiScrapingMonitor


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response["Content-Security-Policy"] = (
            "default-src 'self' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://hcaptcha.com https://*.hcaptcha.com; "
            "script-src-elem 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://hcaptcha.com https://*.hcaptcha.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://hcaptcha.com https://*.hcaptcha.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdnjs.cloudflare.com data:; "
            "frame-src https://hcaptcha.com https://*.hcaptcha.com; "
            "connect-src 'self' https://nominatim.openstreetmap.org https://router.project-osrm.org https://*.tile.openstreetmap.org https://hcaptcha.com https://*.hcaptcha.com;"
        )
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"

        return response


class InputSanitizationMiddleware(MiddlewareMixin):
    suspicious_patterns = [
        r"<script",
        r"javascript:",
        r"onerror=",
        r"onload=",
        r"eval\(",
        r"expression\(",
    ]

    def process_request(self, request):
        if request.method == "POST":
            for key, value in request.POST.items():
                if isinstance(value, str):
                    for pattern in self.suspicious_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            return HttpResponseForbidden("Entrée suspecte détectée")
        return None


class AntiScrapingMiddleware(MiddlewareMixin):
    BOT_USER_AGENTS = [
        r"bot",
        r"crawl",
        r"spider",
        r"scrape",
        r"curl",
        r"wget",
        r"python-requests",
        r"scrapy",
        r"beautifulsoup",
        r"selenium",
        r"headless",
        r"phantom",
        r"automation",
    ]

    SUSPICIOUS_PATTERNS = [r"/api/.*", r"/admin/.*"]

    WHITELISTED_PATHS = [
        r"/api/v1/analytics/survey/statistics/",
        r"/api/v1/analytics/survey/.*",
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self.ip_requests = defaultdict(list)
        self.ip_violations = defaultdict(int)

    def is_whitelisted_path(self, path):
        for pattern in self.WHITELISTED_PATHS:
            if re.match(pattern, path):
                return True
        return False

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def is_bot_user_agent(self, user_agent):
        if not user_agent:
            return True
        user_agent = user_agent.lower()
        for pattern in self.BOT_USER_AGENTS:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return True
        return False

    def check_request_pattern(self, ip, path):
        current_time = time.time()

        self.ip_requests[ip] = [
            t for t in self.ip_requests[ip] if current_time - t < 10
        ]

        if len(self.ip_requests[ip]) > 20:
            return False

        self.ip_requests[ip].append(current_time)
        return True

    def __call__(self, request):
        ip = self.get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        path = request.path

        if self.is_whitelisted_path(path):
            response = self.get_response(request)
            return response

        if self.is_bot_user_agent(user_agent):
            cache_key = f"bot_block_{ip}"
            if cache.get(cache_key):
                AntiScrapingMonitor.log_suspicious_activity(
                    ip, user_agent, path, "Bot user-agent bloqué"
                )
                return JsonResponse(
                    {
                        "error": "Accès refusé",
                        "message": "Activité automatisée détectée",
                    },
                    status=403,
                )

            cache.set(cache_key, True, 3600)
            AntiScrapingMonitor.log_suspicious_activity(
                ip, user_agent, path, "Bot user-agent détecté"
            )
            return JsonResponse(
                {"error": "Accès refusé", "message": "User-Agent non autorisé"},
                status=403,
            )

        if not self.check_request_pattern(ip, path):
            self.ip_violations[ip] += 1

            AntiScrapingMonitor.log_suspicious_activity(
                ip,
                user_agent,
                path,
                f"Trop de requêtes ({len(self.ip_requests[ip])} en 10s)",
            )

            if self.ip_violations[ip] > 3:
                cache_key = f"ip_block_{ip}"
                cache.set(cache_key, True, 7200)
                AntiScrapingMonitor.log_suspicious_activity(
                    ip, user_agent, path, "IP bloquée pour violations répétées"
                )
                return JsonResponse(
                    {
                        "error": "Accès bloqué",
                        "message": "Trop de requêtes détectées. IP bloquée pour 2 heures.",
                    },
                    status=429,
                )

            return JsonResponse(
                {
                    "error": "Limite atteinte",
                    "message": "Trop de requêtes. Veuillez ralentir.",
                },
                status=429,
            )

        cache_key = f"ip_block_{ip}"
        if cache.get(cache_key):
            AntiScrapingMonitor.log_suspicious_activity(
                ip, user_agent, path, "Tentative d'accès depuis IP bloquée"
            )
            return JsonResponse(
                {
                    "error": "Accès bloqué",
                    "message": "Votre IP est temporairement bloquée",
                },
                status=403,
            )

        response = self.get_response(request)
        return response


class RateLimitMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_counts = {}
        self.ip_counts = {}

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def __call__(self, request):
        current_time = time.time()
        ip = self.get_client_ip(request)

        if ip not in self.ip_counts:
            self.ip_counts[ip] = []

        self.ip_counts[ip] = [t for t in self.ip_counts[ip] if current_time - t < 60]

        if len(self.ip_counts[ip]) > 200:
            cache_key = f"rate_limit_{ip}"
            if not cache.get(cache_key):
                cache.set(cache_key, True, 300)

            return JsonResponse(
                {
                    "error": "Limite de taux dépassée",
                    "message": "Trop de requêtes. Réessayez dans 5 minutes.",
                },
                status=429,
            )

        self.ip_counts[ip].append(current_time)

        # Check authenticated user rate limit only if user attribute exists
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user.uid)

            if user_id not in self.request_counts:
                self.request_counts[user_id] = []

            self.request_counts[user_id] = [
                t for t in self.request_counts[user_id] if current_time - t < 60
            ]

            if len(self.request_counts[user_id]) > 100:
                return JsonResponse(
                    {
                        "error": "Limite de taux dépassée",
                        "message": "Trop de requêtes. Veuillez réessayer plus tard.",
                    },
                    status=429,
                )

            self.request_counts[user_id].append(current_time)

        response = self.get_response(request)
        return response
