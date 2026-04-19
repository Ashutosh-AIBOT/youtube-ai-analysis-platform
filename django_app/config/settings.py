import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR   = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", os.getenv("SECRET_KEY", "change-me"))
DEBUG      = os.getenv("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", os.getenv("ALLOWED_HOSTS", "*")).split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",
    "youtube",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF     = "config.urls"
AUTH_USER_MODEL  = "users.User"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [{
    "BACKEND" : "django.template.backends.django.DjangoTemplates",
    "DIRS"    : [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS" : {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

# PostgreSQL on Railway - only email+password stored here
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL:
    import dj_database_url
    ssl_require = not DATABASE_URL.startswith("sqlite")
    DATABASES = {"default": dj_database_url.parse(
        DATABASE_URL, conn_max_age=600, ssl_require=ssl_require)}
else:
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME"  : BASE_DIR / "db.sqlite3",
    }}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 6}},
]
LOGIN_URL           = "/login/"
LOGIN_REDIRECT_URL  = "/"
LOGOUT_REDIRECT_URL = "/login/"

STATIC_URL       = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT      = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "UTC"
USE_TZ        = True

SENTIMENT_SERVICE_URL = os.getenv("SENTIMENT_SERVICE_URL", "http://localhost:8010")
RAG_WORKER_URL        = os.getenv("RAG_WORKER_URL",        "http://localhost:8011")
YOUTUBE_SERVICE_URL   = os.getenv("YOUTUBE_SERVICE_URL",   "http://localhost:8005")
INTERNAL_API_KEY      = os.getenv("INTERNAL_API_KEY",      "mypassword123")
CHROMA_PATH           = os.getenv("CHROMA_PATH",           "./chromadb")
PINECONE_API_KEY      = os.getenv("PINECONE_API_KEY",      "")
PINECONE_INDEX        = os.getenv("PINECONE_INDEX",        "good-lectures")
