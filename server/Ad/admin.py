from django.contrib import admin
from django.core.exceptions import ValidationError
#import cv2
from .models import News, AdVideo, CurrencyRate, BackgroundImage, NewsSource
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