from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.contrib import admin
import sys

class AdConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Ad'

    def ready(self):
        # Инициализируем планировщик только когда запускается runserver
        # или когда запускается WSGI/ASGI сервер
        is_server_command = 'runserver' in sys.argv or 'gunicorn' in sys.argv[0] or 'uvicorn' in sys.argv[0]
        
        if is_server_command:
            from .tasks import SchedulerSingleton
            SchedulerSingleton.get_instance()

        # Отмена регистрации моделей Django APScheduler
        from django_apscheduler.models import DjangoJobExecution, DjangoJob
        try:
            admin.site.unregister(DjangoJobExecution)
        except admin.sites.NotRegistered:
            pass
        try:
            admin.site.unregister(DjangoJob)
        except admin.sites.NotRegistered:
            pass