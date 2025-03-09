from django.test import TestCase
from django.contrib.auth.models import User
from Ad.models import News, NewsRating

class NewsModelTest(TestCase):
    """Тесты для модели News"""
    
    def test_news_creation(self):
        """Тест создания объекта новости"""
        news = News.objects.create(
            title="Тестовая новость",
            description="Это тестовая новость для проверки функциональности"
        )
        self.assertEqual(news.title, "Тестовая новость")
        self.assertEqual(news.description, "Это тестовая новость для проверки функциональности")
        self.assertEqual(news.comments_count, 0)  # Проверка property comments_count


class NewsRatingModelTest(TestCase):
    """Тесты для модели NewsRating"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.news = News.objects.create(
            title="Тестовая новость",
            description="Описание тестовой новости"
        )
    
    def test_dislike_news(self):
        """Тест создания дислайка новости"""
        # Создаем дислайк
        rating = NewsRating.objects.create(
            user=self.user,
            news=self.news,
            is_like=False  # Дизлайк
        )
        
        # Проверяем, что дислайк успешно создан
        self.assertFalse(rating.is_like)
        
        # Проверяем строковое представление
        self.assertIn("дизлайк", str(rating))
        self.assertIn(self.user.username, str(rating))
        self.assertIn(self.news.title, str(rating)) 