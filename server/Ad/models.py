from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User

# Модель новостей
class News(models.Model):
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    date_published = models.DateTimeField(verbose_name="Дата публикации")
    image = models.URLField(max_length=500, verbose_name="Ссылка на изображение", null=True, blank=True)
    background_image = models.ImageField(upload_to='news_backgrounds/', verbose_name="Фоновое изображение", null=True, blank=True)
    link = models.URLField(max_length=1000, unique=True, verbose_name="Ссылка на новость", null=True, blank=True)
    source = models.ForeignKey(
        'NewsSource',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Источник"
    )

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"
        # unique_together = ('title', 'date_published')  # Удалено для устранения конфликта с уникальностью 'link'

    def __str__(self):
        return self.title