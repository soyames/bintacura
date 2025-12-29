from django.utils import translation
from django.conf import settings


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = self._get_language_for_request(request)
        
        translation.activate(language)
        request.LANGUAGE_CODE = language

        response = self.get_response(request)
        
        if hasattr(request, 'LANGUAGE_CODE'):
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME or 'django_language',
                request.LANGUAGE_CODE,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH or '/',
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )

        return response
    
    def _get_language_for_request(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'preferred_language'):
            user_language = request.user.preferred_language or settings.LANGUAGE_CODE
            if user_language in dict(settings.LANGUAGES):
                return user_language
        
        language_cookie = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if language_cookie and language_cookie in dict(settings.LANGUAGES):
            return language_cookie
        
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        if accept_language:
            detected_language = self._parse_accept_language(accept_language)
            if detected_language:
                return detected_language
        
        return settings.LANGUAGE_CODE
    
    def _parse_accept_language(self, accept_language_header):
        supported_languages = dict(settings.LANGUAGES)
        languages = []
        
        for lang_entry in accept_language_header.split(','):
            parts = lang_entry.strip().split(';')
            lang_code = parts[0].strip().lower()[:2]
            
            try:
                quality = 1.0
                if len(parts) > 1 and parts[1].strip().startswith('q='):
                    quality = float(parts[1].strip()[2:])
                languages.append((lang_code, quality))
            except (ValueError, IndexError):
                continue
        
        languages.sort(key=lambda x: x[1], reverse=True)
        
        for lang_code, _ in languages:
            if lang_code in supported_languages:
                return lang_code
        
        return None
