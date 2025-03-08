from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.contrib import admin

class AdConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Ad'

    def ready(self):
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