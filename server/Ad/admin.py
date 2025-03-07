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

# def get_video_duration(file_path):
#     video = cv2.VideoCapture(file_path)
#     total_frames = video.get(cv2.CAP_PROP_FRAME_COUNT)
#     fps = video.get(cv2.CAP_PROP_FPS)
#     duration = total_frames / fps if fps != 0 else 0
#     video.release()
#     return duration