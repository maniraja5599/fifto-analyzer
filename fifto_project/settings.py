from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "django-insecure-your-secret-key-goes-here"
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0', '*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'analyzer',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "fifto_project.urls"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = "fifto_project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",}, {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",}, {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",}, {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",},]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# DhanHQ API Configuration (DATA ONLY - NOT FOR TRADING)
# =============================================================================
# 
# IMPORTANT DISCLAIMER:
# This application uses DhanHQ API ONLY for accessing market data including:
# - Real-time quotes for NIFTY, BANKNIFTY, SENSEX, VIX
# - Historical price data for technical analysis
# - Option chain data for zones calculation
# - Market status and timing information
#
# NO TRADING OPERATIONS are performed through this API
# NO BUY/SELL orders are placed
# NO FUNDS are accessed or transferred
# This is purely for DATA RETRIEVAL and ANALYSIS purposes only
#
# DhanHQ API Access Token and Client ID are required for data access
# =============================================================================

# Your DhanHQ API Credentials (Data API Access Only)
DHAN_CLIENT_ID = os.environ.get('DHAN_CLIENT_ID', '1000491652')  # Your DhanHQ Client ID
DHAN_ACCESS_TOKEN = os.environ.get('DHAN_ACCESS_TOKEN', 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU3NDg2Nzg3LCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTAwMDQ5MTY1MiJ9.kOcdS0SbXvOhipCd30Ck5q80xpPk85VbCSMvPIIB39AckCDDYIM2fO6S5XwteVcxwYODxSesWPchbusTE2OzcQ')

# Market Data Source Configuration
USE_DHAN_API = True  # Set to True to use DhanHQ as primary data source
FALLBACK_TO_NSE = True  # Fallback to static data if DhanHQ fails

# API Usage Limits and Best Practices
DHAN_API_RATE_LIMIT = 1  # Max 1 request per second as per DhanHQ guidelines
DHAN_API_TIMEOUT = 10  # 10 seconds timeout for API requests
DHAN_MAX_RETRIES = 3  # Maximum retry attempts for failed requests

# =============================================================================
# END DhanHQ Configuration
# =============================================================================

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'