from django.contrib import admin
from .models import News, NewsRating

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title', 'description')

@admin.register(NewsRating)
class NewsRatingAdmin(admin.ModelAdmin):
    list_display = ('news', 'user', 'rating_type', 'created_at')
    list_filter = ('rating_type',) 