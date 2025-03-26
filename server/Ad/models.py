from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

# Модель новостей
class News(models.Model):
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    date_published = models.DateTimeField(verbose_name="Дата публикации", default=timezone.now)
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

    def __str__(self):
        return self.title

    @property
    def comments_count(self):
        """Возвращает количество комментариев к новости"""
        return self.comments.count()

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

# Модель фоновых изображений
class BackgroundImage(models.Model):
    image = models.ImageField(upload_to='backgrounds/', verbose_name="Фоновое изображение")

    class Meta:
        verbose_name = "Фоновое изображение"
        verbose_name_plural = "Фоновые изображения"

    def __str__(self):
        return f"Фоновое изображение {self.id}"


class NewsSource(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название источника")
    feed_url = models.URLField(max_length=1000, verbose_name="URL RSS канала")
    is_active = models.BooleanField(default=True, verbose_name="Активный источник")

    class Meta:
        verbose_name = "Источник новостей"
        verbose_name_plural = "Источники новостей"

    def __str__(self):
        return self.name
        
# Модель для оценок новостей
class NewsRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    news = models.ForeignKey(News, on_delete=models.CASCADE, verbose_name="Новость")
    is_like = models.BooleanField(verbose_name="Лайк")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Оценка новости"
        verbose_name_plural = "Оценки новостей"
        unique_together = ('user', 'news')  # Пользователь может оценить новость только один раз

    def __str__(self):
        rating_type = "лайк" if self.is_like else "дизлайк"
        return f"{self.user.username} - {self.news.title} - {rating_type}"

# Модель профиля пользователя для расширения стандартной модели пользователя
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    comments = models.ManyToManyField(
        'NewsComment',
        related_name='user_profiles',
        verbose_name="Комментарии пользователя",
        blank=True
    )
    
    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"
        
    def __str__(self):
        return self.user.username

    def add_comment_activity(self, comment):
        """Добавляет комментарий в активность пользователя"""
        self.comments.add(comment)
        
    def get_recent_activity(self, limit=10):
        """Возвращает последние действия пользователя"""
        return self.comments.select_related('news').order_by('-created_at')[:limit]

# Модель для комментариев к новостям
class NewsComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    news = models.ForeignKey(News, on_delete=models.CASCADE, related_name='comments', verbose_name="Новость")
    text = models.TextField(verbose_name="Текст комментария")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    class Meta:
        verbose_name = "Комментарий к новости"
        verbose_name_plural = "Комментарии к новостям"
        ordering = ['-created_at']  # Сортировка по дате (сначала новые)
        
    def __str__(self):
        return f"{self.user.username} - {self.news.title[:30]}"

class WeatherCache(models.Model):
    city = models.CharField(max_length=100)
    temperature = models.FloatField()
    feels_like = models.FloatField()
    humidity = models.IntegerField()
    pressure = models.IntegerField()
    wind_speed = models.FloatField()
    description = models.CharField(max_length=200)
    icon = models.CharField(max_length=20)
    date = models.DateField()
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('city', 'date')
        
    def __str__(self):
        return f"{self.city} - {self.date} ({self.temperature}°C)"

# Сигнал для автоматического создания профиля пользователя
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Создает профиль пользователя при создании нового пользователя"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Сохраняет профиль пользователя при сохранении пользователя"""
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)
