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
        # Модель курсов валют
class CurrencyRate(models.Model):
    currency_name = models.CharField(max_length=10, verbose_name="Название валюты")
    rate = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Курс")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    symbol = models.CharField(max_length=5, verbose_name="Символ валюты", default="₽")

    class Meta:
        verbose_name = "Курс валюты"
        verbose_name_plural = "Курсы валют"

    def __str__(self):
        return f"{self.currency_name}{self.symbol}: {self.rate}₽"