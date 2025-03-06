from django.db import models
from django.contrib.auth.models import User

class News(models.Model):
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    
    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class NewsRating(models.Model):
    RATING_CHOICES = (
        ('like', 'Лайк'),
        ('dislike', 'Дизлайк'),
    )
    
    news = models.ForeignKey(News, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating_type = models.CharField(max_length=10, choices=RATING_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('news', 'user')
        verbose_name = "Оценка новости"
        verbose_name_plural = "Оценки новостей" 