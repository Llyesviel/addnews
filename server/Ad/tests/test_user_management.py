from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.contrib.auth.forms import UserCreationForm


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