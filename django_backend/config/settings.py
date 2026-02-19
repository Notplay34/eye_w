"""
Django settings for eye_w (внутренний контур Document/Payment).
Использует ту же PostgreSQL, что и FastAPI backend.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-change-in-production")

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "documents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

# База данных — та же PostgreSQL, что и FastAPI
# Берём из DATABASE_URL (postgresql:// или postgresql+asyncpg://) или дефолт
_db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://eye_user:eye_pass@localhost:5432/eye_w",
).replace("postgresql+asyncpg://", "postgresql://")

def _parse_db_url(url):
    if "://" not in url:
        return {}
    url = url.split("://", 1)[1]
    if "@" not in url:
        return {}
    auth, rest = url.split("@", 1)
    user, _, password = auth.partition(":")
    host_port, _, name = rest.partition("/")
    name = name.split("?")[0] or "eye_w"
    host, _, port = host_port.partition(":")
    port = port or "5432"
    return {"NAME": name, "USER": user, "PASSWORD": password, "HOST": host, "PORT": port}

_db = _parse_db_url(_db_url) or {
    "NAME": "eye_w",
    "USER": "eye_user",
    "PASSWORD": "eye_pass",
    "HOST": "localhost",
    "PORT": "5432",
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        **{k: v for k, v in _db.items() if v},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
