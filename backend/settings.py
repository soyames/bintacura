from pathlib import Path
from decouple import config, Csv
import sys, os
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# Environment detection
def detect_environment():
    """Auto-detect the current environment"""
    env = config('ENVIRONMENT', default=None)
    if env:
        return env.lower()
    if os.environ.get('RENDER'):
        return 'production'
    hostname = os.environ.get('HOSTNAME', '').lower()
    if any(x in hostname for x in ['prod', 'production', 'render']):
        return 'production'
    elif any(x in hostname for x in ['staging', 'stage']):
        return 'staging'
    return 'development'

def is_local():
    """Detect if running on local machine"""
    if os.environ.get('RENDER'):
        return False
    cloud_indicators = ['AWS_EXECUTION_ENV', 'KUBERNETES_SERVICE_HOST', 'HEROKU_APP_NAME', 
                       'DYNO', 'GOOGLE_CLOUD_PROJECT', 'AZURE_FUNCTIONS_ENVIRONMENT', 'IS_RENDER']
    for indicator in cloud_indicators:
        if os.environ.get(indicator):
            return False
    return True

def is_production():
    """Check if running in production"""
    return detect_environment() == 'production'

current_env = detect_environment()
_is_local = is_local()

# Print configuration summary
location = 'LOCAL MACHINE' if _is_local else 'RENDER.COM/AWS'
print("\n" + "="*70)
print("BINTACURA ENVIRONMENT CONFIGURATION")
print("="*70)
print(f"Environment:     {current_env.upper()}")
print(f"Location:        {location}")
print(f"Region:          {config('DEPLOYMENT_REGION', default='EU-NORTH-1').upper()}")
print(f"Debug Mode:      {config('DEBUG', default=False, cast=bool)}")
print(f"Database:        {config('DB_HOST', default='localhost')}")
print(f"Email Backend:   {'AWS SES' if config('USE_SES', default=False, cast=bool) else 'SMTP'}")
print(f"Security:        {config('SECURITY_PROFILE', default='moderate')}")
if _is_local:
    print(f"Local Port:      8080")
print("="*70 + "\n")

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

try:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# Site URL for callbacks and webhooks
if _is_local:
    SITE_URL = config('LOCAL_SITE_URL', default='http://127.0.0.1:8080')
else:
    SITE_URL = config('SITE_URL', default='https://bintacura.org')

if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        'https://bintacura.org/',
        'https://www.bintacura.org/',
        'https://*.bintacura.org',
        'https://bintacura.onrender.com',
        'http://localhost',
        'http://localhost',
        'http://127.0.0.1',
        'http://localhost:8080',
        'http://127.0.0.1:8080',
    ]
else:
    CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# Multi-Region Database Configuration
DEPLOYMENT_REGION = config('DEPLOYMENT_REGION', default='eu-north-1')
ENABLE_MULTI_REGION = config('ENABLE_MULTI_REGION', default=False, cast=bool)

# Primary Database (AWS RDS Stockholm or Render Frankfurt depending on deployment)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT', default=5432),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Add Frankfurt (Render) database if multi-region is enabled
# This allows simultaneous connections to both AWS and Render databases
if ENABLE_MULTI_REGION:
    DATABASES['frankfurt'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_FRANKFURT_NAME', default='vitacare_global_db'),
        'USER': env('DB_FRANKFURT_USER', default=env('DB_USER')),
        'PASSWORD': env('DB_FRANKFURT_PASSWORD', default=env('DB_PASSWORD')),
        'HOST': env('DB_FRANKFURT_HOST'),
        'PORT': env('DB_FRANKFURT_PORT', default=5432),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }

# Database router configuration (enable when using multi-region)
# Routes database operations to appropriate regional database
if ENABLE_MULTI_REGION:
    DATABASE_ROUTERS = ['core.db_router.RegionalDatabaseRouter']
SECURITY_STRICT_MODE = config("SECURITY_STRICT_MODE", default=False, cast=bool)

ENABLE_ADVANCED_SECURITY_MIDDLEWARE = config(
    "ENABLE_ADVANCED_SECURITY_MIDDLEWARE",
    default=False,
    cast=bool,
)

PAYMENT_CONFIGURATION = {
    'RESCHEDULE_FEE': 1000,
    'DEFAULT_CONSULTATION_FEE_XOF': 3500,
    'PLATFORM_FEE_RATE': 0.01,
    'PLATFORM_TAX_RATE': 0.18,
}

# Regional Pricing Configuration
REGIONAL_PRICING = {
    'BJ': {  # Benin
        'country_code': 'BJ',
        'currency': 'XOF',
        'default_consultation_fee': 3500,
        'database': 'default',
    },
    'TG': {  # Togo
        'country_code': 'TG',
        'currency': 'XOF',
        'default_consultation_fee': 3500,
        'database': 'default',
    },
    'CI': {  # Côte d'Ivoire
        'country_code': 'CI',
        'currency': 'XOF',
        'default_consultation_fee': 4000,
        'database': 'default',
    },
    'SN': {  # Senegal
        'country_code': 'SN',
        'currency': 'XOF',
        'default_consultation_fee': 4500,
        'database': 'default',
    },
    'ML': {  # Mali
        'country_code': 'ML',
        'currency': 'XOF',
        'default_consultation_fee': 3000,
        'database': 'default',
    },
    'BF': {  # Burkina Faso
        'country_code': 'BF',
        'currency': 'XOF',
        'default_consultation_fee': 3000,
        'database': 'default',
    },
    'NE': {  # Niger
        'country_code': 'NE',
        'currency': 'XOF',
        'default_consultation_fee': 3000,
        'database': 'default',
    },
    'GW': {  # Guinea-Bissau
        'country_code': 'GW',
        'currency': 'XOF',
        'default_consultation_fee': 2500,
        'database': 'default',
    },
    'CM': {  # Cameroon
        'country_code': 'CM',
        'currency': 'XAF',
        'default_consultation_fee': 3500,
        'database': 'default',
    },
    'GA': {  # Gabon
        'country_code': 'GA',
        'currency': 'XAF',
        'default_consultation_fee': 5000,
        'database': 'default',
    },
    'CG': {  # Congo
        'country_code': 'CG',
        'currency': 'XAF',
        'default_consultation_fee': 4000,
        'database': 'default',
    },
    'CF': {  # Central African Republic
        'country_code': 'CF',
        'currency': 'XAF',
        'default_consultation_fee': 3000,
        'database': 'default',
    },
    'TD': {  # Chad
        'country_code': 'TD',
        'currency': 'XAF',
        'default_consultation_fee': 3500,
        'database': 'default',
    },
    'GN': {  # Guinea
        'country_code': 'GN',
        'currency': 'GNF',
        'default_consultation_fee': 35000,
        'database': 'default',
    },
    'NG': {  # Nigeria
        'country_code': 'NG',
        'currency': 'NGN',
        'default_consultation_fee': 5000,
        'database': 'default',
    },
    'GH': {  # Ghana
        'country_code': 'GH',
        'currency': 'GHS',
        'default_consultation_fee': 50,
        'database': 'default',
    },
    'ZA': {  # South Africa
        'country_code': 'ZA',
        'currency': 'ZAR',
        'default_consultation_fee': 500,
        'database': 'default',
    },
    'DE': {  # Germany (Frankfurt)
        'country_code': 'DE',
        'currency': 'EUR',
        'default_consultation_fee': 50,
        'database': 'frankfurt' if ENABLE_MULTI_REGION else 'default',
    },
    'FR': {  # France
        'country_code': 'FR',
        'currency': 'EUR',
        'default_consultation_fee': 45,
        'database': 'frankfurt' if ENABLE_MULTI_REGION else 'default',
    },
    'BE': {  # Belgium
        'country_code': 'BE',
        'currency': 'EUR',
        'default_consultation_fee': 45,
        'database': 'frankfurt' if ENABLE_MULTI_REGION else 'default',
    },
    'US': {  # United States
        'country_code': 'US',
        'currency': 'USD',
        'default_consultation_fee': 50,
        'database': 'default',
    },
}

# Helper function to get regional config
def get_regional_config(country_code):
    """Get regional pricing configuration for a country"""
    return REGIONAL_PRICING.get(country_code, {
        'country_code': country_code,
        'currency': DEFAULT_CURRENCY,
        'default_consultation_fee': DEFAULT_CONSULTATION_FEE_XOF,
        'database': 'default',
    })

RESCHEDULE_FEE = PAYMENT_CONFIGURATION['RESCHEDULE_FEE']
DEFAULT_CONSULTATION_FEE_XOF = PAYMENT_CONFIGURATION['DEFAULT_CONSULTATION_FEE_XOF']
PLATFORM_FEE_RATE = PAYMENT_CONFIGURATION['PLATFORM_FEE_RATE']
PLATFORM_TAX_RATE = PAYMENT_CONFIGURATION['PLATFORM_TAX_RATE']

# FedaPay Configuration
FEDAPAY_ENVIRONMENT = env('FEDAPAY_ENVIRONMENT', default='sandbox')  # 'sandbox' or 'live'

# Select the correct API key based on environment
if FEDAPAY_ENVIRONMENT == 'live':
    FEDAPAY_API_KEY = env('FEDAPAY_SK_LIVE', default='')
    FEDAPAY_PUBLIC_KEY = env('FEDAPAY_PK_LIVE', default='')
    FEDAPAY_WEBHOOK_SECRET = env('FEDAPAY_WEBHOOK_LIVE', default='')
else:  # sandbox
    FEDAPAY_API_KEY = env('FEDAPAY_SK_SANDBOX', default='')
    FEDAPAY_PUBLIC_KEY = env('FEDAPAY_PK_SANDBOX', default='')
    FEDAPAY_WEBHOOK_SECRET = env('FEDAPAY_WEBHOOK_SANDBOX', default='')

# Currency Configuration
DEFAULT_CURRENCY = 'XOF'
SUPPORTED_CURRENCIES = ['USD', 'EUR', 'XOF', 'XAF', 'GNF','NGN', 'GHS', 'ZAR']

# Exchange Rate API (for real-time currency conversion)
EXCHANGE_RATE_API_KEY = env('EXCHANGE_RATE_API_KEY', default='')
EXCHANGE_RATE_API_URL = 'https://api.exchangerate-api.com/v4/latest/XOF'

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "hcaptcha_field",  # hCaptcha for bot protection
    "core",
    "authentication",
    "patient",
    "doctor",
    "appointments",
    "prescriptions",
    "payments",
    "insurance",
    "health_records",
    "communication",
    "ads",
    "analytics",
    "pharmacy",
    "hospital",
    "queue_management",
    "transport",
    "currency_converter",
    "financial",
    "hr",
    "ai",
    "qrcode_generator",
    "sync",  # Offline-first synchronization for business instances
    "super_admin",  # Super admin dashboard and verification system
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.domain_security_middleware.DomainSecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "core.region_middleware.RegionContextMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.language_middleware.UserLanguageMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ADVANCED_SECURITY_MIDDLEWARE = [
    "core.middleware.SecurityHeadersMiddleware",
    "core.security_middleware.RequestSizeMiddleware",
    "core.security_middleware.DDoSProtectionMiddleware",
    "core.security_middleware.BruteForceProtectionMiddleware",
    "core.middleware.InputSanitizationMiddleware",
    "core.security_middleware.SQLInjectionProtectionMiddleware",
    "core.security_middleware.XSSProtectionMiddleware",
    "core.security_middleware.PathTraversalProtectionMiddleware",
    "core.middleware.AntiScrapingMiddleware",
    "core.security_middleware.APIKeyValidationMiddleware",
    "core.middleware.RateLimitMiddleware",
    "core.security_middleware.SecurityAuditMiddleware",
]

# Add advanced security middleware AFTER authentication middleware
if ENABLE_ADVANCED_SECURITY_MIDDLEWARE:
    # Find the index of AuthenticationMiddleware and insert after it
    auth_index = MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware")
    # Insert advanced middleware after authentication
    for i, mw in enumerate(ADVANCED_SECURITY_MIDDLEWARE):
        MIDDLEWARE.insert(auth_index + 1 + i, mw)

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "ads.context_processors.active_ads",
                "core.context_processors.platform_settings",
                "core.context_processors.currency_context",
                "core.context_processors.wallet_context",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"
ASGI_APPLICATION = "backend.asgi.application"



##Render.com Postgres access
#DATABASES = {
#    "default": {
 #       "ENGINE": config("DB_ENGINE"),
  #      "NAME": config("DB_NAME"),
   #     "USER": config("DB_USER"),
    #    "PASSWORD": config("DB_PASSWORD"),
     #   "HOST": config("DB_HOST"),
      #  "PORT": config("DB_PORT"),
       # "OPTIONS": {
        #    "sslmode": "require",
      #  },
   # }
#}

# Additional database connection strings (for reference and debugging)
# These are not used by Django directly but stored for convenience
#INTERNAL_DATABASE_URL = config("INTERNAL_DATABASE_URL", default="")
#EXTERNAL_DATABASE_URL = config("EXTERNAL_DATABASE_URL", default="")
#PSQL_COMMAND = config("PSQL_COMMAND", default="")

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "core.Participant"

LANGUAGE_CODE = "fr"
LANGUAGES = [
    ('fr', 'Français'),
    ('en', 'English'),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

# Language cookie settings for persistent language preference
LANGUAGE_COOKIE_NAME = 'django_language'
LANGUAGE_COOKIE_AGE = 31536000  # 1 year in seconds
LANGUAGE_COOKIE_PATH = '/'
LANGUAGE_COOKIE_DOMAIN = None
LANGUAGE_COOKIE_SECURE = False  # Set to True in production with HTTPS
LANGUAGE_COOKIE_HTTPONLY = False  # False to allow JavaScript access
LANGUAGE_COOKIE_SAMESITE = 'Lax'

TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "BINTACURA Healthcare Platform API",
    "DESCRIPTION": "Comprehensive healthcare platform API supporting multi-role users, appointments, prescriptions, payments, insurance, and telemedicine",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
}

# CORS: Cross-Origin Resource Sharing configuration for frontend access
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only allow all origins in development
# CORS_ALLOWED_ORIGINS: Frontend domains allowed to make API requests
# Production: Add your frontend domain(s) WITH protocol (https://)
# Format: comma-separated list with full protocol
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://localhost:8080,localhost",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True  # Allow cookies/credentials in CORS requests

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=24),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "USER_ID_FIELD": "uid",
    "USER_ID_CLAIM": "uid",
}

CELERY_BROKER_URL = "memory://localhost/"
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_RESULT_EXPIRES = 3600

# Cache Configuration (Phase 11: AI Caching)
# Using local memory cache for minimal storage impact
# Suitable for development and small production deployments
# For larger deployments, consider Redis
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "BINTACURA-cache",
        "OPTIONS": {
            "MAX_ENTRIES": 1000,  # Limit cache size to 1000 entries
        }
    }
}

# Override for testing
if "pytest" in sys.modules or "test" in sys.argv:
    CACHES["default"]["LOCATION"] = "unique-test-cache"


SESSION_ENGINE = "django.contrib.sessions.backends.db"

#TWILIO_ACCOUNT_SID = config("TWILIO_ACCOUNT_SID", default="")
#TWILIO_AUTH_TOKEN = config("TWILIO_AUTH_TOKEN", default="")
#TWILIO_PHONE_NUMBER = config("TWILIO_PHONE_NUMBER", default="")

# ============================================================================
# EMAIL CONFIGURATION - Zoho Mail SMTP (Always Active)
# ============================================================================

# Always use SMTP for email delivery in all environments
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Zoho EU SMTP Configuration
EMAIL_HOST = config("EMAIL_HOST", default="smtppro.zoho.eu")
EMAIL_PORT = config("EMAIL_PORT", default=465, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=True, cast=bool)

# Zoho authentication credentials
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="contacts@bintacura.org")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")

# Email timeout settings
EMAIL_TIMEOUT = config("EMAIL_TIMEOUT", default=30, cast=int)

# Email addresses configuration
# Primary sender email (used for all outbound emails)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="BintaCura <contacts@bintacura.org>")

# Server error notifications email
SERVER_EMAIL = config("SERVER_EMAIL", default="contacts@bintacura.org")

# No-reply email for automated notifications (can be configured separately if needed)
NO_REPLY_EMAIL = config("NO_REPLY_EMAIL", default="no-reply@bintacura.org")

# Admin contact email (for official communications)
CONTACT_EMAIL = config("CONTACT_EMAIL", default="contacts@bintacura.org")

# Admin email addresses (receive server error notifications)
ADMINS = [
    ('BintaCura Admin', config("ADMIN_EMAIL", default="contacts@bintacura.org")),
]

# Manager email addresses (receive broken link notifications)
MANAGERS = ADMINS

# Frontend URL for email templates
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:8000")

# Payment Provider Configuration
# Stripe Configuration
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY", default="")

# Note: FedaPay configuration is at line ~288-298 above

# Regional Payment Provider Configuration (uncomment when deploying to specific regions)
# Mali
# PAYMENT_PROVIDER_MALI = config("PAYMENT_PROVIDER_MALI", default="fedapay")
# FEDAPAY_API_KEY_MALI = config("FEDAPAY_API_KEY_MALI", default=FEDAPAY_API_KEY)
# FEDAPAY_API_SECRET_MALI = config("FEDAPAY_API_SECRET_MALI", default=FEDAPAY_API_SECRET)

# Senegal
# PAYMENT_PROVIDER_SENEGAL = config("PAYMENT_PROVIDER_SENEGAL", default="wave")
# WAVE_API_KEY_SENEGAL = config("WAVE_API_KEY_SENEGAL", default="")
# WAVE_API_SECRET_SENEGAL = config("WAVE_API_SECRET_SENEGAL", default="")

# Benin
# PAYMENT_PROVIDER_BENIN = config("PAYMENT_PROVIDER_BENIN", default="fedapay")
# FEDAPAY_API_KEY_BENIN = config("FEDAPAY_API_KEY_BENIN", default=FEDAPAY_API_KEY)
# FEDAPAY_API_SECRET_BENIN = config("FEDAPAY_API_SECRET_BENIN", default=FEDAPAY_API_SECRET)

# Payment provider mapping (uncomment when enabling multi-region)
# REGIONAL_PAYMENT_PROVIDERS = {
#     'default': {
#         'provider': 'fedapay',
#         'api_key': FEDAPAY_API_KEY,
#         'api_secret': FEDAPAY_API_SECRET,
#     },
#     'mali': {
#         'provider': PAYMENT_PROVIDER_MALI,
#         'api_key': FEDAPAY_API_KEY_MALI,
#         'api_secret': FEDAPAY_API_SECRET_MALI,
#     },
#     'senegal': {
#         'provider': PAYMENT_PROVIDER_SENEGAL,
#         'api_key': WAVE_API_KEY_SENEGAL,
#         'api_secret': WAVE_API_SECRET_SENEGAL,
#     },
#     'benin': {
#         'provider': PAYMENT_PROVIDER_BENIN,
#         'api_key': FEDAPAY_API_KEY_BENIN,
#         'api_secret': FEDAPAY_API_SECRET_BENIN,
#     },
# }

# Leaflet with OpenStreetMap Configuration
# BintaCura uses Leaflet.js and OpenStreetMap for all mapping features
# No Google Maps API key needed - open-source mapping solution
# Leaflet CDN: https://unpkg.com/leaflet@1.9.4/dist/leaflet.css
# OpenStreetMap tiles: https://tile.openstreetmap.org/{z}/{x}/{y}.png

HUGGINGFACE_API_KEY = config("HUGGINGFACE_API_KEY", default="")

LOGIN_URL = "/auth/login/"

# Site URL configuration
if DEBUG:
    SITE_URL = config("SITE_URL", default="http://127.0.0.1:8080")
else:
    SITE_URL = config("SITE_URL", default="https://bintacura.org")

LOGIN_REDIRECT_URL = "/dashboard/patient/"
LOGOUT_REDIRECT_URL = "/auth/login/"

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Smart security settings: Enable in production, allow localhost override
# In production (DEBUG=False), these are enabled by default for security
# For local development, can be overridden via .env
_IS_PRODUCTION = not DEBUG
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=_IS_PRODUCTION, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=_IS_PRODUCTION, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=_IS_PRODUCTION, cast=bool)

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000  # 1 year in production
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_REFERRER_POLICY = "same-origin"

# Additional Security Headers
X_CONTENT_TYPE_OPTIONS = "nosniff"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"  # Prevents cross-origin attacks

# Session Security Settings
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookies
SESSION_COOKIE_SAMESITE = "Lax"  # CSRF protection
SESSION_COOKIE_AGE = 86400  # 24 hours (in seconds)
SESSION_SAVE_EVERY_REQUEST = True  # Extend session on activity
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Keep session for SESSION_COOKIE_AGE

# CSRF Protection Settings
CSRF_COOKIE_HTTPONLY = False  # Must be False for JavaScript access
CSRF_COOKIE_SAMESITE = "Lax"  # CSRF protection
CSRF_USE_SESSIONS = False  # Use cookie-based CSRF tokens
CSRF_COOKIE_NAME = "csrftoken"
CSRF_TRUSTED_ORIGINS = [
    "https://bintacura.onrender.com",
    "https://bintacura.org",
    "https://www.bintacura.org",
    "https://*.bintacura.org",
    "http://localhost",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760

SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

import os

# Import centralized logging configuration
from core.logging_config import get_logging_config

# Create logs directory if it doesn't exist (for local development)
LOGS_DIR = BASE_DIR / "logs"
if not os.path.exists(LOGS_DIR):
    try:
        os.makedirs(LOGS_DIR)
    except (OSError, PermissionError):
        # In production environments like Render, we may not have write permissions
        # In that case, we'll just use console logging
        pass

# Determine if we can use file logging
USE_FILE_LOGGING = os.path.exists(LOGS_DIR) and os.access(LOGS_DIR, os.W_OK)

# Get region-specific logging configuration
LOGGING = get_logging_config(BASE_DIR, DEPLOYMENT_REGION)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ALLOWED_UPLOAD_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]
MAX_UPLOAD_SIZE = 10485760

# ============================================================================
# OFFLINE-FIRST SYNCHRONIZATION SETTINGS
# ============================================================================

# Import celery schedules
from celery.schedules import crontab

# Instance Configuration
# INSTANCE_TYPE: 'CLOUD' for central cloud deployment, 'LOCAL' for on-premise installations
# CRITICAL: This determines whether superuser creation is allowed
INSTANCE_TYPE = config('INSTANCE_TYPE', default='CLOUD')

# Set this to the instance UUID when deploying to a local business installation
# Leave as None for cloud deployments
INSTANCE_ID = config('INSTANCE_ID', default=None)

# Cloud Sync URLs (LOCAL INSTANCES ONLY)
# URLs for local instances to sync with cloud
SYNC_CLOUD_PUSH_URL = config(
    'SYNC_CLOUD_PUSH_URL',
    default='https://www.bintacura.org/api/v1/sync/push/'
)
SYNC_CLOUD_PULL_URL = config(
    'SYNC_CLOUD_PULL_URL',
    default='https://www.bintacura.org/api/v1/sync/pull/'
)

# Sync Configuration
SYNC_BATCH_SIZE = config('SYNC_BATCH_SIZE', default=100, cast=int)  # Events per push batch
SYNC_INTERVAL_MINUTES = config('SYNC_INTERVAL_MINUTES', default=15, cast=int)  # Auto-sync interval

# Update CELERY_BEAT_SCHEDULE if it exists, otherwise create it
if 'CELERY_BEAT_SCHEDULE' not in locals():
    CELERY_BEAT_SCHEDULE = {}

# Add sync tasks to schedule
CELERY_BEAT_SCHEDULE.update({
    # Bidirectional sync (only runs on local instances with INSTANCE_ID set)
    'bidirectional-sync': {
        'task': 'sync.tasks.bidirectional_sync',
        'schedule': crontab(minute=f'*/{SYNC_INTERVAL_MINUTES}'),
        'options': {'expires': 60 * 10}  # Expire after 10 minutes if not executed
    },
    # Cleanup old sync logs (runs on all instances)
    'cleanup-sync-logs': {
        'task': 'sync.tasks.cleanup_old_sync_logs',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        'kwargs': {'days_to_keep': 30}
    },
    # Cleanup synced events (runs on all instances)
    'cleanup-synced-events': {
        'task': 'sync.tasks.cleanup_synced_events',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
        'kwargs': {'days_to_keep': 7}
    },
    # Fetch exchange rates daily
    'fetch-exchange-rates': {
        'task': 'currency_converter.tasks.fetch_exchange_rates',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
    },
    # Cleanup old exchange rates
    'cleanup-old-exchange-rates': {
        'task': 'currency_converter.tasks.cleanup_old_exchange_rates',
        'schedule': crontab(hour=4, minute=0),  # Daily at 4 AM
    },
})

# ============================================================================

if SENTRY_AVAILABLE:
    sentry_sdk.init(
        dsn=config("SENTRY_DSN", default=""),
        integrations=[
            DjangoIntegration(),
            RedisIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.1, cast=float),
        profiles_sample_rate=config(
            "SENTRY_PROFILES_SAMPLE_RATE", default=0.1, cast=float
        ),
        send_default_pii=False,
        environment=config("ENVIRONMENT", default="development"),
        release=config("RELEASE_VERSION", default="1.0.0"),
        before_send=lambda event, hint: event if not DEBUG else None,
    )

# ============================================================================
# hCAPTCHA CONFIGURATION - Bot Protection
# ============================================================================

# hCaptcha Site Key (Public key - visible in HTML)
HCAPTCHA_SITEKEY = config('HCAPTCHA_SITEKEY', default='')

# hCaptcha Secret Key (Private key - used for server-side validation)
HCAPTCHA_SECRET = config('HCAPTCHA_SECRET', default='')

# hCaptcha Widget Configuration
# Prevent widget from rendering script tag (we load it manually in template head)
HCAPTCHA_DEFAULT_CONFIG = {'include_script': False}

# ============================================================================



