from django.contrib import admin
from django.core.exceptions import ValidationError
#import cv2
from .models import News, CurrencyRate, BackgroundImage, NewsSource, CurrencyRateHistory
from django.contrib import messages

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'date_published', 'source')
    search_fields = ('title', 'source__name')
    list_filter = ('source',)
    fields = ('title', 'description', 'date_published', 'image', 'background_image', 'source')
    
@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'feed_url', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'feed_url')
    actions = ['update_news_from_sources']

    @admin.action(description="Обновить новости из выбранных источников")
    def update_news_from_sources(self, request, queryset):
        try:
            from .tasks import SchedulerSingleton
            SchedulerSingleton.fetch_news_from_sources(queryset)
            self.message_user(
                request,
                f"Новости успешно обновлены из {queryset.count()} источников",
                messages.SUCCESS
            )
        except Exception as e:
            self.message_user(
                request,
                f"Ошибка при обновлении новостей: {str(e)}",
                messages.ERROR
            )

@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ('currency_name', 'rate', 'updated_at', 'source')
    list_filter = ('currency_name', 'source')
    search_fields = ('currency_name',)
    date_hierarchy = 'updated_at'
    readonly_fields = ('updated_at',)
    actions = ['update_currency_rates']
    
    @admin.action(description="Обновить курсы валют вручную")
    def update_currency_rates(self, request, queryset):
        try:
            from .tasks import SchedulerSingleton
            SchedulerSingleton.update_currency_job_force()
            self.message_user(
                request,
                "Курсы валют успешно обновлены",
                messages.SUCCESS
            )
        except Exception as e:
            self.message_user(
                request,
                f"Ошибка при обновлении курсов валют: {str(e)}",
                messages.ERROR
            )
            
    def has_add_permission(self, request):
        # Запрещаем добавление новых валют вручную через админку
        # Новые валюты добавляются только через автоматическое обновление
        return False

@admin.register(CurrencyRateHistory)
class CurrencyRateHistoryAdmin(admin.ModelAdmin):
    list_display = ('currency_name', 'rate', 'timestamp', 'source')
    list_filter = ('currency_name', 'source')
    search_fields = ('currency_name',)
    date_hierarchy = 'timestamp'
    readonly_fields = ('currency_name', 'rate', 'timestamp', 'source')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Разрешаем удаление только для очистки старых записей
        return True