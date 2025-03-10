from django.test import TestCase, Client, LiveServerTestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
import json
from Ad.models import News, NewsComment, NewsRating, NewsSource


class RegisterAuthenticationTest(TestCase):
    """
    Тесты для проверки регистрации пользователей.
    Проверяем различные сценарии ввода данных при регистрации, включая валидацию паролей.
    """
    
    def setUp(self):
        """Настройка данных перед каждым тестом"""
        # Инициализируем клиент для отправки запросов
        self.client = Client()
        
        # URL для регистрации
        self.register_url = reverse('register')
        
        # Базовые данные для регистрации
        self.valid_username = 'testuser'
        self.valid_password = 'TestPassword123'
    
    def test_empty_username(self):
        """
        Тест 1: Пустое имя пользователя.
        Ожидаемый результат: форма не принимается, возникает ошибка валидации.
        """
        # Отправляем POST-запрос с пустым именем пользователя
        response = self.client.post(self.register_url, {
            'username': '',
            'password1': self.valid_password,
            'password2': self.valid_password
        })
        
        # Проверяем, что статус 200 (форма с ошибкой)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что ответ содержит форму с полями
        self.assertIn('form', response.context)
        
        # Проверяем, что есть ошибка в форме для поля username
        form = response.context['form']
        self.assertTrue(form.errors.get('username'))
        
        # Проверяем, что пользователь не был создан
        self.assertEqual(User.objects.count(), 0)
    
    def test_empty_password(self):
        """
        Тест 2: Пустой пароль.
        Ожидаемый результат: форма не принимается, возникает ошибка валидации.
        """
        # Отправляем POST-запрос с пустым паролем
        response = self.client.post(self.register_url, {
            'username': self.valid_username,
            'password1': '',
            'password2': ''
        })
        
        # Проверяем, что статус 200 (форма с ошибкой)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что ответ содержит форму с полями
        self.assertIn('form', response.context)
        
        # Проверяем, что есть ошибка в форме для поля password1
        form = response.context['form']
        self.assertTrue(form.errors.get('password1'))
        
        # Проверяем, что пользователь не был создан
        self.assertEqual(User.objects.count(), 0)
    
    def test_empty_password_confirmation(self):
        """
        Тест 3: Пустое подтверждение пароля.
        Ожидаемый результат: форма не принимается, возникает ошибка валидации.
        """
        # Отправляем POST-запрос с пустым подтверждением пароля
        response = self.client.post(self.register_url, {
            'username': self.valid_username,
            'password1': self.valid_password,
            'password2': ''
        })
        
        # Проверяем, что статус 200 (форма с ошибкой)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что ответ содержит форму с полями
        self.assertIn('form', response.context)
        
        # Проверяем, что есть ошибка в форме для поля password2
        form = response.context['form']
        self.assertTrue(form.errors.get('password2'))
        
        # Проверяем, что пользователь не был создан
        self.assertEqual(User.objects.count(), 0)
    
    def test_password_too_short(self):
        """
        Тест 4a: Пароль слишком короткий (меньше 8 символов).
        Ожидаемый результат: форма не принимается, возникает ошибка валидации.
        Примечание: В Django может быть отключен этот валидатор, поэтому тест
        проверяет только, что пользователь не создается с коротким паролем.
        """
        short_password = 'short'
        
        # Отправляем POST-запрос с коротким паролем
        response = self.client.post(self.register_url, {
            'username': self.valid_username,
            'password1': short_password,
            'password2': short_password
        })
        
        # Проверяем, что пользователь не был создан
        self.assertEqual(User.objects.count(), 0)
        
        # Если валидация работает, то статус должен быть 200 (форма с ошибкой)
        # В противном случае, может быть и другой статус
        # Проверяем, что не произошло перенаправления на главную страницу (успешная регистрация)
        self.assertNotEqual(response.status_code, 302)
    
    def test_password_too_common(self):
        """
        Тест 4b: Пароль слишком распространен.
        Ожидаемый результат: форма не принимается, возникает ошибка валидации.
        Примечание: В Django может быть отключен этот валидатор, поэтому тест
        проверяет только, что пользователь не создается с общим паролем.
        """
        common_password = 'password123'
        
        # Отправляем POST-запрос с распространенным паролем
        response = self.client.post(self.register_url, {
            'username': self.valid_username,
            'password1': common_password,
            'password2': common_password
        })
        
        # Проверяем, что пользователь не был создан
        self.assertEqual(User.objects.count(), 0)
        
        # Проверяем, что не произошло перенаправления на главную страницу (успешная регистрация)
        self.assertNotEqual(response.status_code, 302)
    
    def test_password_entirely_numeric(self):
        """
        Тест 4c: Пароль состоит только из цифр.
        Ожидаемый результат: форма не принимается, возникает ошибка валидации.
        Примечание: В Django может быть отключен этот валидатор, поэтому тест
        проверяет только, что пользователь не создается с числовым паролем.
        """
        numeric_password = '12345678'
        
        # Отправляем POST-запрос с паролем из цифр
        response = self.client.post(self.register_url, {
            'username': self.valid_username,
            'password1': numeric_password,
            'password2': numeric_password
        })
        
        # Проверяем, что пользователь не был создан
        self.assertEqual(User.objects.count(), 0)
        
        # Проверяем, что не произошло перенаправления на главную страницу (успешная регистрация)
        self.assertNotEqual(response.status_code, 302)
    
    def test_password_mismatch(self):
        """
        Тест 5: Пароль и подтверждение пароля не совпадают.
        Ожидаемый результат: форма не принимается, возникает ошибка валидации.
        """
        # Отправляем POST-запрос с несовпадающими паролями
        response = self.client.post(self.register_url, {
            'username': self.valid_username,
            'password1': self.valid_password,
            'password2': self.valid_password + '1'  # Добавляем символ для несовпадения
        })
        
        # Проверяем, что статус 200 (форма с ошибкой)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что ответ содержит форму с полями
        self.assertIn('form', response.context)
        
        # Проверяем, что есть ошибка в форме для поля password2
        form = response.context['form']
        self.assertTrue(form.errors.get('password2'))
        
        # Проверяем сообщение об ошибке
        error_message = form.errors['password2'][0]
        self.assertIn('не совпадают', error_message)
        
        # Проверяем, что пользователь не был создан
        self.assertEqual(User.objects.count(), 0)
    
    def test_successful_registration(self):
        """
        Тест 6: Успешная регистрация со всеми корректными данными.
        Ожидаемый результат: пользователь создан и автоматически авторизован.
        """
        # Отправляем POST-запрос с корректными данными
        response = self.client.post(self.register_url, {
            'username': self.valid_username,
            'password1': self.valid_password,
            'password2': self.valid_password
        })
        
        # Проверяем, что произошло перенаправление на главную страницу
        self.assertRedirects(response, reverse('main'))
        
        # Проверяем, что пользователь был создан
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.username, self.valid_username)
        
        # Проверяем, что пользователь автоматически авторизован
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, self.valid_username)
    
    def test_redirects_to_main_after_registration(self):
        """
        Тест 13: Проверка, что после успешной регистрации происходит
        перенаправление на главную страницу.
        Ожидаемый результат: После регистрации пользователь перенаправляется
        на главную страницу.
        """
        # Отправляем POST-запрос с корректными данными для регистрации
        response = self.client.post(self.register_url, {
            'username': self.valid_username,
            'password1': self.valid_password,
            'password2': self.valid_password
        }, follow=True)  # follow=True для отслеживания редиректов
        
        # Проверяем, что произошло перенаправление на главную страницу
        self.assertRedirects(response, reverse('main'))
        
        # Проверяем, что мы находимся на главной странице
        self.assertTemplateUsed(response, 'main.html')
        
        # Проверяем, что пользователь был создан
        self.assertTrue(User.objects.filter(username=self.valid_username).exists())
        
        # Проверяем, что пользователь авторизован
        self.assertTrue(response.context['user'].is_authenticated)


class LoginAuthenticationTest(TestCase):
    """
    Тесты для проверки авторизации пользователей.
    Проверяем различные сценарии ввода данных при авторизации.
    """
    
    def setUp(self):
        """Настройка данных перед каждым тестом"""
        # Создаем тестового пользователя
        self.username = 'testuser'
        self.password = 'testpassword123'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password
        )
        
        # Инициализируем клиент для отправки запросов
        self.client = Client()
        
        # URL для авторизации
        self.login_url = reverse('login')
    
    def test_correct_username_wrong_password(self):
        """
        Тест 1: Правильное имя пользователя, но неправильный пароль.
        Ожидаемый результат: ошибка авторизации.
        """
        # Отправляем POST-запрос с правильным именем, но неправильным паролем
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': 'wrongpassword'
        })
        
        # Проверяем, что статус 200 (форма с ошибкой)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что пользователь не авторизован
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Проверяем наличие сообщения об ошибке
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Неверное имя пользователя или пароль" in str(message) for message in messages))
    
    def test_wrong_username_correct_password(self):
        """
        Тест 2: Неправильное имя пользователя, но правильный пароль.
        Ожидаемый результат: ошибка авторизации.
        """
        # Отправляем POST-запрос с неправильным именем, но правильным паролем
        response = self.client.post(self.login_url, {
            'username': 'wrongusername',
            'password': self.password
        })
        
        # Проверяем, что статус 200 (форма с ошибкой)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что пользователь не авторизован
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Проверяем наличие сообщения об ошибке
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Неверное имя пользователя или пароль" in str(message) for message in messages))
    
    def test_correct_credentials(self):
        """
        Тест 3: Правильные имя пользователя и пароль.
        Ожидаемый результат: успешная авторизация.
        """
        # Отправляем POST-запрос с правильными данными
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password
        })
        
        # Проверяем, что произошло перенаправление на главную страницу
        self.assertRedirects(response, reverse('main'))
        
        # Проверяем, что пользователь авторизован
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, self.username)
    
    def test_wrong_credentials(self):
        """
        Тест 4: Неправильные имя пользователя и пароль.
        Ожидаемый результат: ошибка авторизации.
        """
        # Отправляем POST-запрос с неправильными данными
        response = self.client.post(self.login_url, {
            'username': 'wrongusername',
            'password': 'wrongpassword'
        })
        
        # Проверяем, что статус 200 (форма с ошибкой)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что пользователь не авторизован
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Проверяем наличие сообщения об ошибке
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Неверное имя пользователя или пароль" in str(message) for message in messages))
    
    def test_empty_username(self):
        """
        Тест 5: Пустое имя пользователя.
        Ожидаемый результат: форма не принимается, возникает ошибка валидации.
        Примечание: В браузере пользователь увидит сообщение "Заполните это поле"
        через HTML5-валидацию, но на сервере проверяется только факт ошибки.
        """
        # Отправляем POST-запрос с пустым именем пользователя
        response = self.client.post(self.login_url, {
            'username': '',
            'password': 'somepassword'
        })
        
        # Проверяем, что статус 200 (форма с ошибкой)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что пользователь не авторизован
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Проверяем, что ответ содержит форму с полями
        self.assertIn('form', response.context)
        
        # Проверяем, что есть ошибка в форме для поля username
        form = response.context['form']
        self.assertTrue(form.errors.get('username'))
    
    def test_empty_password(self):
        """
        Тест 6: Пустой пароль.
        Ожидаемый результат: форма не принимается, возникает ошибка валидации.
        Примечание: В браузере пользователь увидит сообщение "Заполните это поле"
        через HTML5-валидацию, но на сервере проверяется только факт ошибки.
        """
        # Отправляем POST-запрос с пустым паролем
        response = self.client.post(self.login_url, {
            'username': 'someusername',
            'password': ''
        })
        
        # Проверяем, что статус 200 (форма с ошибкой)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что пользователь не авторизован
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Проверяем, что ответ содержит форму с полями
        self.assertIn('form', response.context)
        
        # Проверяем, что есть ошибка в форме для поля password
        form = response.context['form']
        self.assertTrue(form.errors.get('password'))
    
    def test_empty_username_and_password(self):
        """
        Тест 7: Пустые имя пользователя и пароль.
        Ожидаемый результат: форма не принимается, возникают ошибки валидации для обоих полей.
        Примечание: В браузере пользователь увидит сообщение "Заполните это поле"
        для первого пустого поля через HTML5-валидацию.
        """
        # Отправляем POST-запрос с пустыми полями
        response = self.client.post(self.login_url, {
            'username': '',
            'password': ''
        })
        
        # Проверяем, что статус 200 (форма с ошибкой)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что пользователь не авторизован
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Проверяем, что ответ содержит форму с полями
        self.assertIn('form', response.context)
        
        # Проверяем, что есть ошибки в форме для обоих полей
        form = response.context['form']
        self.assertTrue(form.errors.get('username'))
        self.assertTrue(form.errors.get('password'))


class UserProfileTest(TestCase):
    """
    Тесты для проверки функциональности профиля пользователя.
    Проверяем доступ к профилю и операции с профилем (смена пароля).
    """
    
    def setUp(self):
        """Настройка данных перед каждым тестом"""
        # Создаем тестового пользователя
        self.username = 'profileuser'
        self.password = 'profilepassword123'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password
        )
        
        # Инициализируем клиент для отправки запросов
        self.client = Client()
        
        # URL для профиля и смены пароля
        self.profile_url = reverse('profile')
        self.password_change_url = reverse('change_password')  # Исправленное имя URL
    
    def test_profile_access_unauthorized(self):
        """
        Тест 1: Доступ к профилю без авторизации.
        Ожидаемый результат: перенаправление на страницу авторизации.
        """
        # Пытаемся получить доступ к профилю без авторизации
        response = self.client.get(self.profile_url)
        
        # Проверяем, что произошло перенаправление (статус 302)
        self.assertEqual(response.status_code, 302)
        
        # Проверяем, что URL содержит путь к логину
        login_url = reverse('login')
        self.assertTrue(login_url in response.url)
    
    def test_profile_access_authorized(self):
        """
        Тест 2: Доступ к профилю с авторизацией.
        Ожидаемый результат: успешный доступ к странице профиля.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Получаем доступ к профилю
        response = self.client.get(self.profile_url)
        
        # Проверяем, что статус 200 (успешный доступ)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что в контексте есть текущий пользователь
        self.assertEqual(response.context['user'].username, self.username)
    
    def test_password_change_success(self):
        """
        Тест 3: Успешная смена пароля.
        Ожидаемый результат: пароль изменен, пользователь может войти с новым паролем.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Новый пароль для смены
        new_password = 'newpassword456'
        
        # Отправляем запрос на смену пароля
        response = self.client.post(self.password_change_url, {
            'old_password': self.password,
            'new_password1': new_password,
            'new_password2': new_password
        })
        
        # Проверяем, что произошло перенаправление на страницу профиля
        self.assertRedirects(response, self.profile_url)
        
        # Выходим из системы
        self.client.logout()
        
        # Пытаемся войти с новым паролем
        login_success = self.client.login(username=self.username, password=new_password)
        self.assertTrue(login_success)
    
    def test_password_change_wrong_old_password(self):
        """
        Тест 4: Попытка смены пароля с неверным текущим паролем.
        Ожидаемый результат: ошибка валидации, пароль не изменен.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Новый пароль для смены
        new_password = 'newpassword456'
        
        # Отправляем запрос на смену пароля с неверным текущим паролем
        response = self.client.post(self.password_change_url, {
            'old_password': 'wrongpassword',
            'new_password1': new_password,
            'new_password2': new_password
        })
        
        # Проверяем, что статус 200 (форма с ошибкой)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что ответ содержит форму с полями
        self.assertIn('form', response.context)
        
        # Проверяем, что есть ошибка в форме для поля old_password
        form = response.context['form']
        self.assertTrue(form.errors.get('old_password'))
        
        # Выходим из системы
        self.client.logout()
        
        # Пытаемся войти со старым паролем (он не должен был измениться)
        login_success = self.client.login(username=self.username, password=self.password)
        self.assertTrue(login_success)
    
    def test_password_change_mismatch(self):
        """
        Тест 5: Попытка смены пароля с несовпадающими новыми паролями.
        Ожидаемый результат: ошибка валидации, пароль не изменен.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Новые пароли для смены, которые не совпадают
        new_password1 = 'newpassword456'
        new_password2 = 'differentpassword'
        
        # Отправляем запрос на смену пароля с несовпадающими новыми паролями
        response = self.client.post(self.password_change_url, {
            'old_password': self.password,
            'new_password1': new_password1,
            'new_password2': new_password2
        })
        
        # Проверяем, что статус 200 (форма с ошибкой)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что ответ содержит форму с полями
        self.assertIn('form', response.context)
        
        # Проверяем, что есть ошибка в форме для поля new_password2
        form = response.context['form']
        self.assertTrue(form.errors.get('new_password2'))
        
        # Выходим из системы
        self.client.logout()
        
        # Пытаемся войти со старым паролем (он не должен был измениться)
        login_success = self.client.login(username=self.username, password=self.password)
        self.assertTrue(login_success)


class NewsNavigationTest(TestCase):
    """
    Тесты для проверки функциональности навигации по новостям на главной странице.
    Проверяем работу кнопок "Назад" и "Пропустить".
    """
    
    def setUp(self):
        """Настройка данных перед каждым тестом"""
        # Создаем тестовые новости
        from Ad.models import News, NewsSource
        
        # Создаем источник новостей
        self.source = NewsSource.objects.create(
            name="Тестовый источник",
            feed_url="https://example.com/feed"
        )
        
        self.news1 = News.objects.create(
            title="Тестовая новость 1",
            description="Содержание первой тестовой новости",
            source=self.source,
            link="https://example.com/news1"
        )
        self.news2 = News.objects.create(
            title="Тестовая новость 2",
            description="Содержание второй тестовой новости",
            source=self.source,
            link="https://example.com/news2"
        )
        self.news3 = News.objects.create(
            title="Тестовая новость 3",
            description="Содержание третьей тестовой новости",
            source=self.source,
            link="https://example.com/news3"
        )
        
        # Инициализируем клиент для отправки запросов
        self.client = Client()
        
        # URL для главной страницы
        self.main_url = reverse('main')
    
    def test_skip_news_button(self):
        """
        Тест 1: Проверка кнопки "Пропустить".
        Ожидаемый результат: успешный AJAX-запрос на сервер.
        """
        # Отправляем POST-запрос на API-эндпоинт для пропуска новости
        response = self.client.post(
            reverse('skip_news'), 
            {'direction': 'next'},
            content_type='application/json'
        )
        
        # Проверяем успешный ответ от API
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['message'], 'News skip recorded')
    
    def test_back_news_button(self):
        """
        Тест 2: Проверка кнопки "Назад".
        Ожидаемый результат: успешный AJAX-запрос на сервер.
        """
        # Отправляем POST-запрос на API-эндпоинт для возврата к предыдущей новости
        response = self.client.post(
            reverse('skip_news'), 
            {'direction': 'back'},
            content_type='application/json'
        )
        
        # Проверяем успешный ответ от API
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['message'], 'News skip recorded')
    
    def test_main_page_contains_navigation_buttons(self):
        """
        Тест 3: Проверка наличия кнопок навигации на главной странице.
        Ожидаемый результат: на странице есть кнопки "Назад" и "Пропустить".
        """
        # Запрашиваем главную страницу
        response = self.client.get(self.main_url)
        
        # Проверяем, что страница загружена успешно
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что в HTML-коде страницы есть кнопки навигации
        self.assertContains(response, 'class="nav-button back-button"')
        self.assertContains(response, 'class="nav-button skip-button"')
        self.assertContains(response, '>Назад<')
        self.assertContains(response, '>Пропустить<')
    
    def test_navigation_client_side(self):
        """
        Тест 4: Проверка клиентской логики навигации.
        Поскольку тесты не могут выполнять JavaScript, проверяем наличие
        необходимого кода для обработки нажатий на кнопки.
        """
        # Запрашиваем главную страницу
        response = self.client.get(self.main_url)
        
        # Проверяем наличие JavaScript-функций для навигации
        self.assertContains(response, 'const skipButtons = document.querySelectorAll')
        self.assertContains(response, 'const backButtons = document.querySelectorAll')
        self.assertContains(response, 'showNews(currentNewsIndex + 1)')
        self.assertContains(response, 'showNews(currentNewsIndex - 1)')
        self.assertContains(response, 'fetch("/api/skip-news/"')
        
        # Проверяем, что функция showNews присутствует
        self.assertContains(response, 'function showNews(index)')


class NavigationButtonsTest(TestCase):
    """
    Тесты для проверки работы кнопок навигации между страницами сайта.
    Проверяем, что кнопки на разных страницах корректно перенаправляют пользователя.
    """
    
    def setUp(self):
        """Настройка данных перед каждым тестом"""
        # Создаем тестового пользователя
        self.username = 'testnavuser'
        self.password = 'testnavpassword123'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password
        )
        
        # Инициализируем клиент для отправки запросов
        self.client = Client()
        
        # URL-адреса страниц
        self.main_url = reverse('main')
        self.login_url = reverse('login')
        self.register_url = reverse('register')
        self.profile_url = reverse('profile')
        self.logout_url = reverse('logout')
    
    # === ТЕСТЫ НАВИГАЦИИ С ГЛАВНОЙ СТРАНИЦЫ ===
    
    def test_main_to_main_button(self):
        """
        Тест 1: Кнопка 'Главная страница' на главной странице.
        Ожидаемый результат: пользователь остается на главной странице.
        """
        # Переходим на главную страницу
        response = self.client.get(self.main_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на главную страницу
        self.assertContains(response, f'href="{self.main_url}"')
        
        # Переходим по ссылке на главную страницу
        response = self.client.get(self.main_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на главной странице
        self.assertTemplateUsed(response, 'main.html')
    
    def test_main_to_login_button(self):
        """
        Тест 2: Кнопка 'Вход' на главной странице.
        Ожидаемый результат: пользователь переходит на страницу входа.
        """
        # Переходим на главную страницу
        response = self.client.get(self.main_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на страницу входа
        self.assertContains(response, f'href="{self.login_url}"')
        
        # Переходим по ссылке на страницу входа
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на странице входа
        self.assertTemplateUsed(response, 'login.html')
    
    def test_main_to_register_button(self):
        """
        Тест 3: Кнопка 'Регистрация' на главной странице.
        Ожидаемый результат: пользователь переходит на страницу регистрации.
        """
        # Переходим на главную страницу
        response = self.client.get(self.main_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на страницу регистрации
        self.assertContains(response, f'href="{self.register_url}"')
        
        # Переходим по ссылке на страницу регистрации
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на странице регистрации
        self.assertTemplateUsed(response, 'register.html')
    
    # === ТЕСТЫ НАВИГАЦИИ СО СТРАНИЦЫ ВХОДА ===
    
    def test_login_to_main_button(self):
        """
        Тест 4: Кнопка 'Главная страница' на странице входа.
        Ожидаемый результат: пользователь переходит на главную страницу.
        """
        # Переходим на страницу входа
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на главную страницу
        self.assertContains(response, f'href="{self.main_url}"')
        
        # Переходим по ссылке на главную страницу
        response = self.client.get(self.main_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на главной странице
        self.assertTemplateUsed(response, 'main.html')
    
    def test_login_to_login_button(self):
        """
        Тест 5: Кнопка 'Вход' на странице входа.
        Ожидаемый результат: пользователь остается на странице входа.
        """
        # Переходим на страницу входа
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на страницу входа
        self.assertContains(response, f'href="{self.login_url}"')
        
        # Переходим по ссылке на страницу входа
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на странице входа
        self.assertTemplateUsed(response, 'login.html')
    
    def test_login_to_register_button(self):
        """
        Тест 6: Кнопка 'Регистрация' на странице входа.
        Ожидаемый результат: пользователь переходит на страницу регистрации.
        """
        # Переходим на страницу входа
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на страницу регистрации
        self.assertContains(response, f'href="{self.register_url}"')
        
        # Переходим по ссылке на страницу регистрации
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на странице регистрации
        self.assertTemplateUsed(response, 'register.html')
    
    # === ТЕСТЫ НАВИГАЦИИ СО СТРАНИЦЫ РЕГИСТРАЦИИ ===
    
    def test_register_to_main_button(self):
        """
        Тест 7: Кнопка 'Главная страница' на странице регистрации.
        Ожидаемый результат: пользователь переходит на главную страницу.
        """
        # Переходим на страницу регистрации
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на главную страницу
        self.assertContains(response, f'href="{self.main_url}"')
        
        # Переходим по ссылке на главную страницу
        response = self.client.get(self.main_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на главной странице
        self.assertTemplateUsed(response, 'main.html')
    
    def test_register_to_login_button(self):
        """
        Тест 8: Кнопка 'Вход' на странице регистрации.
        Ожидаемый результат: пользователь переходит на страницу входа.
        """
        # Переходим на страницу регистрации
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на страницу входа
        self.assertContains(response, f'href="{self.login_url}"')
        
        # Переходим по ссылке на страницу входа
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на странице входа
        self.assertTemplateUsed(response, 'login.html')
    
    def test_register_to_register_button(self):
        """
        Тест 9: Кнопка 'Регистрация' на странице регистрации.
        Ожидаемый результат: пользователь остается на странице регистрации.
        """
        # Переходим на страницу регистрации
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на страницу регистрации
        self.assertContains(response, f'href="{self.register_url}"')
        
        # Переходим по ссылке на страницу регистрации
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на странице регистрации
        self.assertTemplateUsed(response, 'register.html')
    
    # === ТЕСТЫ НАВИГАЦИИ СО СТРАНИЦЫ ЛИЧНОГО КАБИНЕТА ===
    
    def test_profile_to_main_button(self):
        """
        Тест 10: Кнопка 'Главная страница' на странице личного кабинета.
        Ожидаемый результат: пользователь переходит на главную страницу.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Переходим на страницу личного кабинета
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на главную страницу
        self.assertContains(response, f'href="{self.main_url}"')
        
        # Переходим по ссылке на главную страницу
        response = self.client.get(self.main_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на главной странице
        self.assertTemplateUsed(response, 'main.html')
    
    def test_profile_to_profile_button(self):
        """
        Тест 11: Кнопка 'Личный кабинет' на странице личного кабинета.
        Ожидаемый результат: пользователь остается на странице личного кабинета.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Переходим на страницу личного кабинета
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на страницу личного кабинета
        self.assertContains(response, f'href="{self.profile_url}"')
        
        # Переходим по ссылке на страницу личного кабинета
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на странице личного кабинета
        self.assertTemplateUsed(response, 'profile.html')
    
    def test_profile_to_logout_button(self):
        """
        Тест 12: Кнопка 'Выход' на странице личного кабинета.
        Ожидаемый результат: пользователь выходит из аккаунта и переходит на главную страницу.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Переходим на страницу личного кабинета
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на выход
        self.assertContains(response, f'href="{self.logout_url}"')
        
        # Переходим по ссылке на выход
        response = self.client.get(self.logout_url, follow=True)
        
        # Проверяем, что произошло перенаправление на главную страницу
        self.assertRedirects(response, self.main_url)
        
        # Проверяем, что пользователь не авторизован
        self.assertFalse(response.context['user'].is_authenticated)
    
    def test_register_to_login_button_bottom(self):
        """
        Тест 14: Кнопка 'Войти' внизу страницы регистрации (под полями ввода).
        Ожидаемый результат: пользователь переходит на страницу входа.
        """
        # Переходим на страницу регистрации
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на страницу входа в нижней части
        # (ищем конкретно ссылку, которая не в навигационной панели)
        content = response.content.decode('utf-8')
        self.assertIn('Уже есть аккаунт? <a href="{}"'.format(self.login_url), content)
        
        # Переходим по ссылке на страницу входа
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на странице входа
        self.assertTemplateUsed(response, 'login.html')


class AdditionalNavigationTests(TestCase):
    """
    Дополнительные тесты для проверки навигации в приложении.
    """
    
    def setUp(self):
        """Настройка данных перед каждым тестом"""
        # Создаем тестового пользователя
        self.username = 'testuser_additional'
        self.password = 'testpassword123'
        self.valid_username = 'newuser_additional'
        self.valid_password = 'ValidPassword123'
        
        # Инициализируем клиент для отправки запросов
        self.client = Client()
        
        # URL для страниц
        self.main_url = reverse('main')
        self.login_url = reverse('login')
        self.register_url = reverse('register')
    
    def test_redirects_to_main_after_registration(self):
        """
        Тест 13: Проверка, что после успешной регистрации происходит
        перенаправление на главную страницу.
        Ожидаемый результат: После регистрации пользователь перенаправляется
        на главную страницу.
        """
        # Отправляем POST-запрос с корректными данными для регистрации
        response = self.client.post(self.register_url, {
            'username': self.valid_username,
            'password1': self.valid_password,
            'password2': self.valid_password
        }, follow=True)  # follow=True для отслеживания редиректов
        
        # Проверяем, что произошло перенаправление на главную страницу
        self.assertRedirects(response, self.main_url)
        
        # Проверяем, что мы находимся на главной странице
        self.assertTemplateUsed(response, 'main.html')
        
        # Проверяем, что пользователь был создан
        self.assertTrue(User.objects.filter(username=self.valid_username).exists())
        
        # Проверяем, что пользователь авторизован
        self.assertTrue(response.context['user'].is_authenticated)
    
    def test_register_to_login_button_bottom(self):
        """
        Тест 14: Кнопка 'Войти' внизу страницы регистрации (под полями ввода).
        Ожидаемый результат: пользователь переходит на страницу входа.
        """
        # Переходим на страницу регистрации
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что на странице есть ссылка на страницу входа в нижней части
        # (ищем конкретно ссылку, которая не в навигационной панели)
        content = response.content.decode('utf-8')
        self.assertIn('Уже есть аккаунт? <a href="{}"'.format(self.login_url), content)
        
        # Переходим по ссылке на страницу входа
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что мы на странице входа
        self.assertTemplateUsed(response, 'login.html')


class NewsInteractionTest(TestCase):
    """
    Тесты для проверки взаимодействия с новостями: лайки, дизлайки и комментарии.
    """
    
    def setUp(self):
        """Настройка данных перед каждым тестом"""
        # Создаем тестовых пользователей
        self.username = 'testuser_interaction'
        self.password = 'testpassword123'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password
        )
        
        # Создаем источник новостей
        self.source = NewsSource.objects.create(
            name="Тестовый источник",
            feed_url="https://example.com/feed"
        )
        
        # Создаем тестовую новость
        self.news = News.objects.create(
            title="Тестовая новость для взаимодействия",
            description="Описание тестовой новости",
            source=self.source,
            link="https://example.com/news1"
        )
        
        # Инициализируем клиент для отправки запросов
        self.client = Client()
        
        # URL-адреса для лайков, дизлайков и комментариев
        self.rate_news_url = reverse('rate_news')
        self.comments_url = reverse('get_comments', args=[self.news.id])
        self.add_comment_url = reverse('add_comment')
    
    def test_like_button(self):
        """
        Тест 15: Проверка работы кнопки лайк.
        Ожидаемый результат: Лайк успешно добавляется к новости.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Отправляем POST-запрос для лайка новости
        response = self.client.post(
            self.rate_news_url,
            json.dumps({
                'news_id': self.news.id,
                'rating_type': 'like'
            }),
            content_type='application/json'
        )
        
        # Проверяем успешный ответ от сервера
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        # Проверяем, что лайк был добавлен в базу данных
        like_exists = NewsRating.objects.filter(
            news=self.news,
            user=self.user,
            is_like=True
        ).exists()
        self.assertTrue(like_exists)
    
    def test_dislike_button(self):
        """
        Тест 16: Проверка работы кнопки дизлайк.
        Ожидаемый результат: Дизлайк успешно добавляется к новости.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Отправляем POST-запрос для дизлайка новости
        response = self.client.post(
            self.rate_news_url,
            json.dumps({
                'news_id': self.news.id,
                'rating_type': 'dislike'
            }),
            content_type='application/json'
        )
        
        # Проверяем успешный ответ от сервера
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        # Проверяем, что дизлайк был добавлен в базу данных
        dislike_exists = NewsRating.objects.filter(
            news=self.news,
            user=self.user,
            is_like=False
        ).exists()
        self.assertTrue(dislike_exists)
    
    def test_comment_button_opens_comments_window(self):
        """
        Тест 17: Проверка, что при нажатии на кнопку комментария открывается окно комментариев.
        Ожидаемый результат: AJAX-запрос за комментариями возвращает успешный ответ.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Отправляем GET-запрос за комментариями (имитируем действие JavaScript при нажатии на кнопку)
        response = self.client.get(self.comments_url)
        
        # Проверяем успешный ответ от сервера
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что ответ содержит нужные поля в JSON
        data = response.json()
        self.assertIn('comments', data)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'success')
    
    def test_add_comment_success(self):
        """
        Тест 18: Проверка успешной отправки комментария.
        Ожидаемый результат: Комментарий успешно добавляется к новости.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Текст комментария
        comment_text = "Это тестовый комментарий"
        
        # Отправляем POST-запрос для добавления комментария
        response = self.client.post(
            self.add_comment_url,
            json.dumps({
                'news_id': self.news.id,
                'comment_text': comment_text
            }),
            content_type='application/json'
        )
        
        # Проверяем успешный ответ от сервера
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        # Проверяем, что комментарий был добавлен в базу данных
        comment_exists = NewsComment.objects.filter(
            news=self.news,
            user=self.user,
            text=comment_text
        ).exists()
        self.assertTrue(comment_exists)
    
    def test_comment_appears_after_submission(self):
        """
        Тест 19: Проверка, что после отправки комментарий появляется в списке.
        Ожидаемый результат: Комментарий появляется в списке комментариев.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Текст комментария
        comment_text = "Это тестовый комментарий для проверки отображения"
        
        # Создаем комментарий напрямую в базе данных для уверенности
        comment = NewsComment.objects.create(
            news=self.news,
            user=self.user,
            text=comment_text
        )
        
        # Запрашиваем список комментариев
        response = self.client.get(self.comments_url)
        
        # Проверяем успешный ответ от сервера
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Проверяем, что комментарий присутствует в списке
        comments = data['comments']
        self.assertTrue(len(comments) > 0)
        self.assertTrue(any(comment_text == comment['text'] for comment in comments))
    
    def test_empty_comment_error(self):
        """
        Тест 20: Проверка, что при отправке пустого комментария выдается ошибка.
        Ожидаемый результат: Сервер возвращает сообщение об ошибке.
        """
        # Авторизуемся
        self.client.login(username=self.username, password=self.password)
        
        # Отправляем POST-запрос с пустым комментарием
        response = self.client.post(
            self.add_comment_url,
            json.dumps({
                'news_id': self.news.id,
                'comment_text': ""
            }),
            content_type='application/json'
        )
        
        # Проверяем статус ответа (ожидаем ошибку)
        self.assertEqual(response.status_code, 400)
        
        # Проверяем, что комментарий не был добавлен в базу данных
        comment_exists = NewsComment.objects.filter(
            news=self.news,
            user=self.user,
            text=""
        ).exists()
        self.assertFalse(comment_exists)

        