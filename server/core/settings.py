"""
Django settings for core project.

Generated by 'django-admin startproject' using Django 5.1.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import os
from pathlib import Path
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.wsgi import get_wsgi_application

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
# Читаем .env файл, который находится в корне проекта
environ.Env.read_env(os.path.join(BASE_DIR, '..', '.env.debug'))

TEST_STAND = env.bool("TEST_STAND", default=False)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-development-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=True)  # Для тестирования используем URL /test-404/

#ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
# ALLOWED_HOSTS = [
#     '*',
#     'https://yz5h-xf63-g6c8.gw-1a.dockhost.net'
# ]

# Обязательно добавляем локальные хосты в ALLOWED_HOSTS
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost', '*'])


# Application definition

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'Ad.apps.AdConfig',
    'django_apscheduler',
    'rest_framework',
]

# Debug toolbar в режиме разработки
if DEBUG:
    # INSTALLED_APPS += ['debug_toolbar']  # Временно отключаем Debug Toolbar для отладки
    pass

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'Ad.middleware.Custom404Middleware',  # Добавляем наше middleware
]

# Debug toolbar middleware в режиме разработки
if DEBUG:
    # MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # Временно отключаем Debug Toolbar middleware
    pass

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # Если используете кастомные шаблоны, добавьте пути сюда
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.static',
                'django.template.context_processors.request',  # Необходим для доступа к request в шаблонах
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Добавляем специальную настройку для обслуживания статических файлов в режиме production
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Настройка для обработки 404 и других ошибок
WSGI_APPLICATION = 'core.wsgi.application'

# Обновляем middleware для обработки статических файлов
if not DEBUG:
    MIDDLEWARE.append('whitenoise.middleware.WhiteNoiseMiddleware')

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Используется SQLite для простоты
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

if TEST_STAND:
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.postgresql_psycopg2',
          'NAME': env("POSTGRES_DB"),
          'USER': env("POSTGRES_USER"),
          'PASSWORD': env("POSTGRES_PASSWORD"),
           'HOST': env("DB_HOST"),
           'PORT': env("DB_PORT"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, '..', 'static_collected')
STATIC_URL = env('STATIC_URL', default='/static/')
if not STATIC_URL.endswith('/'):
    STATIC_URL += '/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'Ad', 'static'),
]

# Media files
MEDIA_URL = env('MEDIA_URL', default='/media/')
if not MEDIA_URL.endswith('/'):
    MEDIA_URL += '/'
MEDIA_ROOT = os.path.join(BASE_DIR, '..', 'static', 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'Ad': {  # Логгер для всего приложения Ad
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'Ad.tasks': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'Ad.views': {  # Логгер специально для views.py
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

JAZZMIN_SETTINGS = {
    "title": "AdNews Admin",
    "site_brand": "AdNews",
    #"site_logo": "path/to/logo.png",
    "welcome_sign": "Добро пожаловать в админку AdNews",
    # Добавьте дополнительные настройки по необходимости
}

# CORS
trust_hosts = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'http://127.0.0.1:9000',
    'http://localhost:9000',
    'http://127.0.0.1:8888'
]
CSRF_TRUSTED_ORIGINS = trust_hosts
# CORS_ORIGIN_WHITELIST = trust_hosts
CORS_ALLOWED_ORIGINS = trust_hosts
CORS_ALLOW_CREDENTIALS = True

DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20 МБ
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# Debug toolbar settings
INTERNAL_IPS = ['127.0.0.1']
