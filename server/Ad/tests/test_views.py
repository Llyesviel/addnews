from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from Ad.models import News, NewsRating

class MainPageViewTest(TestCase):
    """Тесты для представления главной страницы"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        # Создаем несколько новостей
        for i in range(5):
            News.objects.create(
                title=f"Новость {i+1}",
                description=f"Описание новости {i+1}"
            )
    
    def test_main_page_view(self):
        """Тест отображения главной страницы"""
        response = self.client.get(reverse('main'))
        
        # Проверяем успешный ответ
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что новости переданы в контекст
        self.assertIn('news_list', response.context)
        self.assertEqual(len(response.context['news_list']), 5)
        
        # Проверяем, что используется правильный шаблон
        self.assertTemplateUsed(response, 'main.html')


class NewsListWithRatingsTest(TestCase):
    """Тесты для представления списка новостей с рейтингами пользователя"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        
        # Создаем несколько новостей
        self.news1 = News.objects.create(
            title="Новость 1",
            description="Описание новости 1"
        )
        
        self.news2 = News.objects.create(
            title="Новость 2",
            description="Описание новости 2"
        )
        
        # Создаем рейтинг для первой новости
        NewsRating.objects.create(
            user=self.user,
            news=self.news1,
            is_like=True  # Лайк
        )
    
    def test_news_list_with_user_ratings(self):
        """Тест получения списка новостей с рейтингами пользователя"""
        self.client.login(username='testuser', password='testpassword')
        
        response = self.client.get(reverse('main'))
        
        # Проверяем успешный ответ
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что в контексте есть информация о новостях
        news_list = response.context['news_list']
        
        # Проверяем, что у первой новости есть лайк от текущего пользователя
        for news in news_list:
            if news.id == self.news1.id:
                # Проверяем, как именно представление добавляет информацию о рейтинге
                # Это зависит от реализации вашего представления
                # Возможно, это атрибут user_rating или is_liked_by_user
                # Здесь мы предполагаем, что существует атрибут user_liked
                self.assertTrue(hasattr(news, 'user_liked') or hasattr(news, 'user_rating'))
                if hasattr(news, 'user_liked'):
                    self.assertTrue(news.user_liked)
                elif hasattr(news, 'user_rating'):
                    self.assertEqual(news.user_rating, 'like') 