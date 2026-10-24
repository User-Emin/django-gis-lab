from django.utils.csp import CSP

from .base import *  # noqa: F403

# Les 27: productie-instellingen, allemaal via omgevingsvariabelen met veilige defaults.
DEBUG = False
SECURE_SSL_REDIRECT = env_bool("DJANGO_SSL_REDIRECT", True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# HSTS: één jaar, subdomeinen en preload mee. Alleen op een domein waar alles op HTTPS draait;
# in een test-omgeving terug te zetten met DJANGO_HSTS_SECONDS=0 (of 3600).
SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_SUBDOMAINS", True)  # noqa: F405
SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", True)  # noqa: F405
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
# Alleen invullen als de site achter een https-origin met een ander host staat.
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")  # noqa: F405

# Les 27: Content-Security-Policy eerst in Report-Only (de admin en de Vite-kaart gebruiken
# inline stijlen); handhaven pas nadat de meldingen zijn nagelopen.
MIDDLEWARE.append("django.middleware.csp.ContentSecurityPolicyMiddleware")  # noqa: F405
SECURE_CSP_REPORT_ONLY = {
    "default-src": [CSP.SELF],
    "img-src": [CSP.SELF, "data:", "https:"],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "frame-ancestors": [CSP.NONE],
}

# Les 25: whitenoise serveert de statische bestanden uit de container (collectstatic in de build).
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Les 27: gestructureerde logging (JSON, één regel per gebeurtenis) naar stdout.
LOGGING["formatters"]["json"] = {"()": "projectkaart.logging_config.JsonFormatter"}  # noqa: F405
LOGGING["handlers"]["console"]["formatter"] = "json"  # noqa: F405
