from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.core.cache import cache
from collections import defaultdict
import time
import hashlib
from .security_monitor import SecurityMonitor
from .security_config import SecurityConfig


class DDoSProtectionMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        self.ip_request_timestamps = defaultdict(list)
        self.ip_data_volume = defaultdict(int)
        self.ip_endpoint_counts = defaultdict(lambda: defaultdict(int))
        self.config = SecurityConfig.get_profile()

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def check_ddos_attack(self, ip, path):
        current_time = time.time()

        self.ip_request_timestamps[ip] = [
            t for t in self.ip_request_timestamps[ip] if current_time - t < 1
        ]

        requests_per_second = self.config.get('ddos_requests_per_second', 10)
        if len(self.ip_request_timestamps[ip]) > requests_per_second:
            return True, "flood_attack"

        self.ip_request_timestamps[ip].append(current_time)

        minute_requests = [
            t for t in self.ip_request_timestamps[ip] if current_time - t < 60
        ]
        requests_per_minute = self.config.get('ddos_requests_per_minute', 300)
        if len(minute_requests) > requests_per_minute:
            return True, "sustained_attack"

        self.ip_endpoint_counts[ip][path] += 1
        endpoint_limit = self.config.get('ddos_endpoint_limit', 50)
        if self.ip_endpoint_counts[ip][path] > endpoint_limit:
            return True, "endpoint_hammering"

        return False, None

    def __call__(self, request):
        if not self.config.get('enable_ddos_protection', True):
            return self.get_response(request)
        
        ip = self.get_client_ip(request)
        path = request.path
        
        if SecurityConfig.is_ip_whitelisted(ip) or SecurityConfig.is_path_exempt(path, 'static'):
            return self.get_response(request)

        cache_key = f"ddos_block_{ip}"
        if cache.get(cache_key):
            return JsonResponse(
                {
                    "error": "Accès bloqué",
                    "message": "Votre IP a été temporairement bloquée pour activité suspecte",
                },
                status=403,
            )

        is_attack, attack_type = self.check_ddos_attack(ip, path)

        if is_attack:
            block_duration = self.config.get('ddos_block_duration', 3600)
            cache.set(cache_key, True, block_duration)

            SecurityMonitor.log_security_event(
                "ddos_attack",
                ip,
                {"attack_type": attack_type, "path": path},
                "critical",
            )

            cache_key_log = f"ddos_log_{ip}"
            log_data = {
                "ip": ip,
                "attack_type": attack_type,
                "path": path,
                "timestamp": time.time(),
            }
            cache.set(cache_key_log, log_data, 86400)

            return JsonResponse(
                {
                    "error": "Trop de requêtes",
                    "message": f"Activité anormale détectée. Accès bloqué pour {block_duration // 60} minutes.",
                },
                status=429,
            )

        response = self.get_response(request)
        return response


class SQLInjectionProtectionMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.config = SecurityConfig.get_profile()
        # Use relaxed patterns to reduce false positives
        self.SQL_PATTERNS = SecurityConfig.RELAXED_SQL_PATTERNS

    def check_sql_injection(self, value):
        import re

        if not isinstance(value, str):
            return False
        
        # Skip very short values
        if len(value) < 5:
            return False

        value_upper = value.upper()
        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                return True
        return False

    def process_request(self, request):
        if not self.config.get('enable_sql_injection_protection', True):
            return None
        
        ip = request.META.get("REMOTE_ADDR", "")
        
        if SecurityConfig.is_ip_whitelisted(ip) or SecurityConfig.is_path_exempt(request.path):
            return None

        if request.method in ["POST", "PUT", "PATCH"]:
            for key, value in request.POST.items():
                if self.check_sql_injection(value):
                    cache_key = f"sql_injection_attempt_{ip}"
                    attempts = cache.get(cache_key, 0)
                    cache.set(cache_key, attempts + 1, 3600)

                    SecurityMonitor.log_security_event(
                        "sql_injection",
                        ip,
                        {"field": key, "attempts": attempts + 1, "value_preview": value[:50]},
                        "critical",
                    )

                    block_threshold = self.config.get('sql_injection_block_attempts', 3)
                    if attempts >= block_threshold:
                        cache.set(f"ip_block_{ip}", True, 86400)

                    return JsonResponse(
                        {
                            "error": "Requête invalide",
                            "message": "Tentative d'injection SQL détectée",
                        },
                        status=400,
                    )

        if request.method == "GET":
            for key, value in request.GET.items():
                if self.check_sql_injection(value):
                    SecurityMonitor.log_security_event(
                        "sql_injection",
                        ip,
                        {"field": key, "method": "GET", "value_preview": value[:50]},
                        "high",
                    )
                    return JsonResponse(
                        {
                            "error": "Requête invalide",
                            "message": "Paramètres suspects détectés",
                        },
                        status=400,
                    )

        return None


class XSSProtectionMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.config = SecurityConfig.get_profile()
        # Use relaxed patterns to reduce false positives
        self.XSS_PATTERNS = SecurityConfig.RELAXED_XSS_PATTERNS

    def check_xss(self, value):
        import re

        if not isinstance(value, str):
            return False
        
        # Skip very short values
        if len(value) < 5:
            return False

        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    def process_request(self, request):
        if not self.config.get('enable_xss_protection', True):
            return None
        
        if SecurityConfig.is_path_exempt(request.path):
            return None
        
        if request.method in ["POST", "PUT", "PATCH"]:
            for key, value in request.POST.items():
                if self.check_xss(value):
                    ip = request.META.get("REMOTE_ADDR", "")
                    SecurityMonitor.log_security_event(
                        "xss_attack", ip, {"field": key, "value_preview": value[:50]}, "high"
                    )
                    return JsonResponse(
                        {
                            "error": "Requête invalide",
                            "message": "Contenu potentiellement dangereux détecté",
                        },
                        status=400,
                    )

        return None


class PathTraversalProtectionMiddleware(MiddlewareMixin):
    TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.",
        r"%2e%2e",
        r"%252e%252e",
        r"\.\.\\",
        r"%5c%5c",
    ]

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.config = SecurityConfig.get_profile()

    def check_path_traversal(self, value):
        import re

        if not isinstance(value, str):
            return False

        for pattern in self.TRAVERSAL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    def process_request(self, request):
        if not self.config.get('enable_path_traversal_protection', True):
            return None
        
        if SecurityConfig.is_path_exempt(request.path):
            return None
        
        path = request.path

        if self.check_path_traversal(path):
            ip = request.META.get("REMOTE_ADDR", "")
            SecurityMonitor.log_security_event(
                "path_traversal", ip, {"path": path}, "high"
            )
            return JsonResponse(
                {"error": "Accès refusé", "message": "Chemin invalide détecté"},
                status=403,
            )

        for key, value in request.GET.items():
            if self.check_path_traversal(value):
                return JsonResponse(
                    {
                        "error": "Requête invalide",
                        "message": "Paramètres suspects détectés",
                    },
                    status=400,
                )

        return None


class RequestSizeMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.config = SecurityConfig.get_profile()

    def process_request(self, request):
        max_size = self.config.get('request_max_size', 10 * 1024 * 1024)
        
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.META.get("CONTENT_LENGTH")

            if content_length:
                content_length = int(content_length)
                if content_length > max_size:
                    return JsonResponse(
                        {
                            "error": "Requête trop volumineuse",
                            "message": f"Taille maximale autorisée: {max_size // (1024 * 1024)}MB",
                        },
                        status=413,
                    )

        return None


class BruteForceProtectionMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        self.login_attempts = defaultdict(list)
        self.config = SecurityConfig.get_profile()

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def __call__(self, request):
        if not self.config.get('enable_brute_force_protection', True):
            return self.get_response(request)
        
        if request.path in ["/api/v1/auth/login/", "/auth/login/"]:
            ip = self.get_client_ip(request)
            
            if SecurityConfig.is_ip_whitelisted(ip):
                return self.get_response(request)
            
            current_time = time.time()

            cache_key = f"login_block_{ip}"
            if cache.get(cache_key):
                block_duration = self.config.get('brute_force_block_duration', 900)
                return JsonResponse(
                    {
                        "error": "Accès temporairement bloqué",
                        "message": f"Trop de tentatives de connexion. Réessayez dans {block_duration // 60} minutes.",
                    },
                    status=429,
                )

            time_window = self.config.get('brute_force_window', 300)
            self.login_attempts[ip] = [
                t for t in self.login_attempts[ip] if current_time - t < time_window
            ]

            max_attempts = self.config.get('brute_force_attempts', 5)
            if len(self.login_attempts[ip]) >= max_attempts:
                block_duration = self.config.get('brute_force_block_duration', 900)
                cache.set(cache_key, True, block_duration)
                SecurityMonitor.log_security_event(
                    "brute_force",
                    ip,
                    {"attempts": len(self.login_attempts[ip])},
                    "critical",
                )
                return JsonResponse(
                    {
                        "error": "Accès bloqué",
                        "message": f"Trop de tentatives de connexion. Compte bloqué pour {block_duration // 60} minutes.",
                    },
                    status=429,
                )

            if request.method == "POST":
                self.login_attempts[ip].append(current_time)

        response = self.get_response(request)
        return response


class APIKeyValidationMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.config = SecurityConfig.get_profile()

    def process_request(self, request):
        if not self.config.get('enable_api_key_validation', False):
            return None
        
        path = request.path

        # Skip exempt paths
        if SecurityConfig.is_path_exempt(path):
            return None

        if path.startswith("/api/v1/"):
            api_key = request.META.get("HTTP_X_API_KEY")

            if not api_key and not request.user.is_authenticated:
                user_agent = request.META.get("HTTP_USER_AGENT", "")
                # Allow trusted browsers and testing tools
                if not SecurityConfig.is_trusted_user_agent(user_agent):
                    return JsonResponse(
                        {
                            "error": "Authentification requise",
                            "message": "Clé API ou authentification utilisateur requise",
                        },
                        status=401,
                    )

        return None


class SecurityAuditMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def __call__(self, request):
        ip = self.get_client_ip(request)
        path = request.path
        method = request.method
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        suspicious_actions = [
            "/admin/",
            "/api/v1/core/participants/",
            "/api/v1/core/wallets/",
        ]

        for action_path in suspicious_actions:
            if path.startswith(action_path) and method in [
                "POST",
                "PUT",
                "DELETE",
                "PATCH",
            ]:
                cache_key = f"audit_{ip}_{hashlib.md5(path.encode()).hexdigest()}"
                audit_data = {
                    "ip": ip,
                    "path": path,
                    "method": method,
                    "user_agent": user_agent,
                    "timestamp": time.time(),
                    "user": str(request.user)
                    if request.user.is_authenticated
                    else "Anonymous",
                }
                cache.set(cache_key, audit_data, 86400)

        response = self.get_response(request)
        return response
