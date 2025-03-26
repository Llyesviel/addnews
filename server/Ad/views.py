from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from .models import News, CurrencyRate, BackgroundImage, NewsRating, UserProfile, NewsComment
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from itertools import cycle
from django.urls import reverse
import json
import logging
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import calendar
import requests
from .weather_utils import weather_service


def redirect_to_main(request):
    return redirect('main')


def main_page(request):
    news_list = list(News.objects.all().order_by('-date_published')[:10])
    currency_rates = CurrencyRate.objects.all()
    background_images = list(BackgroundImage.objects.all())
    current_time = now()

    if background_images:
        bg_cycle = cycle(background_images)
        for news in news_list:
            news.assigned_background_url = next(bg_cycle).image.url
    else:
        for news in news_list:
            news.assigned_background_url = '/static/default_background.jpg'

    # Добавляем количество лайков и дизлайков для каждой новости
    for news in news_list:
        news.likes_count = NewsRating.objects.filter(news=news, is_like=True).count()
        news.dislikes_count = NewsRating.objects.filter(news=news, is_like=False).count()
        # Свойство comments_count вычисляется автоматически, не нужно его устанавливать
        
        # Если пользователь аутентифицирован, определяем его оценку
        if request.user.is_authenticated:
            try:
                rating = NewsRating.objects.get(user=request.user, news=news)
                news.user_rating = 'like' if rating.is_like else 'dislike'
            except NewsRating.DoesNotExist:
                news.user_rating = None
        else:
            news.user_rating = None

    return render(request, 'main.html', {
        'news_list': news_list,
        'currency_rates': currency_rates,
        'current_time': current_time
    })


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('main')
            else:
                messages.error(request, "Неверное имя пользователя или пароль.")
        else:
            messages.error(request, "Неверное имя пользователя или пароль.")
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)  # Создаем профиль пользователя
            login(request, user)
            return redirect('main')
    else:
        form = UserCreationForm()

    return render(request, 'register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('main')


@login_required
def profile_view(request):
    # Получаем последние комментарии пользователя
    recent_activity = request.user.userprofile.get_recent_activity()
    
    return render(request, 'profile.html', {
        'user': request.user,
        'recent_activity': recent_activity
    })


@login_required
@require_POST
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # Обновление хеша сессии
        messages.success(request, 'Ваш пароль был успешно изменен!')
        return redirect('profile')
    else:
        messages.error(request, 'Пожалуйста, исправьте ошибки ниже.')

    return render(request, 'profile.html', {'form': form})


@csrf_exempt
@require_POST
def rate_news(request):
    logger = logging.getLogger('Ad.views')
    logger.debug(f"rate_news called: PATH={request.path}, METHOD={request.method}")
    
    try:
        # Логируем детали запроса
        logger.debug(f"POST data: {request.POST}")
        body_text = request.body.decode('utf-8') if request.body else None
        logger.debug(f"Body: {body_text}")
        
        # Пробуем получить данные из POST
        news_id = request.POST.get('news_id')
        rating_type = request.POST.get('rating_type')
        
        # Если данных нет в POST, пробуем из тела запроса
        if not news_id or not rating_type:
            try:
                data = json.loads(body_text)
                logger.debug(f"JSON data: {data}")
                news_id = data.get('news_id')
                rating_type = data.get('rating_type')
            except Exception as e:
                logger.error(f"Error parsing JSON: {str(e)}")
        
        logger.debug(f"Parsed data: news_id={news_id}, rating_type={rating_type}")
        
        if not news_id or not rating_type:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'})

        news = get_object_or_404(News, id=news_id)
        
        # Проверяем, авторизован ли пользователь
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'message': 'Пользователь не авторизован'
            })

        # Проверяем, уже оценил ли пользователь эту новость
        try:
            rating = NewsRating.objects.get(user=request.user, news=news)
            # Если тип оценки совпадает с текущей - удаляем оценку
            if (rating.is_like and rating_type == 'like') or (not rating.is_like and rating_type == 'dislike'):
                rating.delete()
                return JsonResponse({
                    'status': 'removed',
                    'likes': NewsRating.objects.filter(news=news, is_like=True).count(),
                    'dislikes': NewsRating.objects.filter(news=news, is_like=False).count()
                })
            else:
                # Изменяем тип оценки
                rating.is_like = rating_type == 'like'
                rating.save()
        except NewsRating.DoesNotExist:
            # Создаем новую оценку
            rating = NewsRating(user=request.user, news=news, is_like=rating_type == 'like')
            rating.save()

        return JsonResponse({
            'status': 'success',
            'likes': NewsRating.objects.filter(news=news, is_like=True).count(),
            'dislikes': NewsRating.objects.filter(news=news, is_like=False).count()
        })
    except Exception as e:
        logger.error(f"Error in rate_news: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@require_POST
def skip_news(request):
    """
    Функция для регистрации пропуска новости
    """
    logger = logging.getLogger('Ad.views')
    logger.debug(f"skip_news вызван: PATH={request.path}, METHOD={request.method}")
    
    try:
        # Здесь можно добавить логику для отслеживания пропусков,
        # например, сохранять информацию в базе данных
        
        # Возвращаем успешный JSON-ответ
        return JsonResponse({
            'status': 'success',
            'message': 'News skip recorded'
        })
    except Exception as e:
        logger.error(f"Ошибка в skip_news: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


def page_not_found(request, exception):
    """
    Обработчик ошибки 404 - страница не найдена
    """
    # Получаем актуальные курсы валют для отображения в футере
    from .models import CurrencyRate
    currency_rates = CurrencyRate.objects.all()

    # Возвращаем страницу с правильным статусом 404
    return render(request, '404.html', {
        'currency_rates': currency_rates
    }, status=404)


def test_404(request):
    """
    Тестовая страница 404 для отображения дизайна страницы ошибки
    """
    logger = logging.getLogger('Ad.views')
    logger.debug(f"test_404 вызван для пути: {request.path}")
    
    currency_rates = CurrencyRate.objects.all()
    
    # Отображаем страницу ошибки
    return render(request, '404.html', {
        'currency_rates': currency_rates
    })


def redirect_to_404(request):
    """
    Функция перенаправления всех несуществующих URL на страницу test-404
    """
    logger = logging.getLogger('Ad.views')
    logger.debug(f"redirect_to_404 вызван для пути: {request.path}")
    
    # Перенаправляем на страницу test-404
    # Важно! Используем redirect (временное перенаправление 302) вместо HttpResponseRedirect
    # Это предотвращает проблемы с кэшированием и повторными запросами
    return redirect('test_404')


@csrf_exempt
def get_comments(request, news_id):
    """
    Получение комментариев к новости
    """
    logger = logging.getLogger('Ad.views')
    logger.debug(f"get_comments called for news_id={news_id}")
    
    try:
        news = get_object_or_404(News, id=news_id)
        comments = NewsComment.objects.filter(news=news).select_related('user')
        
        # Форматируем комментарии для передачи в JSON
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'username': comment.user.username,
                'text': comment.text,
                'created_at': comment.created_at.strftime('%d.%m.%Y %H:%M'),
                'is_owner': request.user.is_authenticated and request.user.id == comment.user.id
            })
        
        return JsonResponse({
            'status': 'success',
            'comments': comments_data
        })
    except Exception as e:
        logger.error(f"Error in get_comments: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


@csrf_exempt
@require_POST
def add_comment(request):
    """
    Добавление комментария к новости
    """
    logger = logging.getLogger('Ad.views')
    logger.debug(f"add_comment called: PATH={request.path}, METHOD={request.method}")
    
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Пользователь не авторизован'
        }, status=401)
    
    try:
        # Получаем данные из запроса
        body_text = request.body.decode('utf-8') if request.body else None
        logger.debug(f"Body: {body_text}")
        
        # Пробуем получить данные из POST или JSON
        news_id = request.POST.get('news_id')
        comment_text = request.POST.get('comment_text')
        
        if not news_id or not comment_text:
            try:
                data = json.loads(body_text)
                logger.debug(f"JSON data: {data}")
                news_id = data.get('news_id')
                comment_text = data.get('comment_text')
            except Exception as e:
                logger.error(f"Error parsing JSON: {str(e)}")
        
        logger.debug(f"Parsed data: news_id={news_id}, comment_text={comment_text}")
        
        if not news_id or not comment_text:
            return JsonResponse({
                'status': 'error',
                'message': 'Не указан идентификатор новости или текст комментария'
            }, status=400)
        
        # Получаем новость и сохраняем комментарий
        news = get_object_or_404(News, id=news_id)
        comment = NewsComment(user=request.user, news=news, text=comment_text)
        comment.save()
        
        # Добавляем комментарий в активность пользователя
        profile = request.user.userprofile
        profile.add_comment_activity(comment)
        
        return JsonResponse({
            'status': 'success',
            'comment': {
                'id': comment.id,
                'username': comment.user.username,
                'text': comment.text,
                'created_at': comment.created_at.strftime('%d.%m.%Y %H:%M'),
                'is_owner': True
            }
        })
    except Exception as e:
        logger.error(f"Error in add_comment: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


class CustomHTMLCalendar(calendar.HTMLCalendar):
    def formatmonth(self, theyear, themonth, withyear=True):
        v = []
        a = v.append
        a('<table border="0" cellpadding="0" cellspacing="0" class="month">')
        a('\n')
        a(self.formatmonthname(theyear, themonth, withyear=withyear))
        a('\n')
        a(self.formatweekheader())
        a('\n')
        for week in self.monthdays2calendar(theyear, themonth):
            a(self.formatweek(week))
            a('\n')
        a('</table>')
        a('\n')
        return ''.join(v)

    def formatday(self, day, weekday):
        if day == 0:
            return '<td class="noday">&nbsp;</td>'  # Пустая ячейка
        else:
            return f'<td class="{self.cssclasses[weekday]}">{day}</td>'

def get_calendar(request, year, month):
    cal = CustomHTMLCalendar(firstweekday=calendar.MONDAY)
    html_calendar = cal.formatmonth(year, month)
    return JsonResponse({'calendar': html_calendar})

def currency_charts(request):
    """View function for the currency charts page."""
    currency_rates = CurrencyRate.objects.all()
    
    # Получаем список валют для отображения в селекторе
    available_currencies = [
        {'code': rate.currency_name, 'symbol': rate.symbol, 'rate': float(rate.rate)}
        for rate in currency_rates
    ]
    
    return render(request, 'currency_charts.html', {
        'currency_rates': currency_rates,
        'available_currencies': available_currencies
    })


@require_POST
def get_currency_history(request):
    """API-endpoint для получения исторических данных о курсах валют."""
    try:
        data = json.loads(request.body)
        currency_code = data.get('currency_code')
        period = data.get('period', 'month')
        
        if not currency_code:
            return JsonResponse({'status': 'error', 'message': 'Не указан код валюты'})
            
        # Для криптовалют используем тестовые данные, так как ЦБ не предоставляет их историю
        if currency_code in ['BTC', 'ETH']:
            # Генерируем тестовые данные для криптовалют
            return JsonResponse({
                'status': 'success',
                'data': generate_test_crypto_data(currency_code, period)
            })
        
        # Для обычных валют пытаемся получить данные из RSS ЦБ РФ
        try:
            history_data = fetch_currency_history_from_cb(currency_code, period)
            return JsonResponse({
                'status': 'success',
                'data': history_data
            })
        except Exception as e:
            logging.error(f"Ошибка при получении истории курсов: {str(e)}")
            # Если не удалось получить реальные данные, используем тестовые
            return JsonResponse({
                'status': 'success',
                'data': generate_test_currency_data(currency_code, period)
            })
            
    except Exception as e:
        logging.error(f"Ошибка в get_currency_history: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


def fetch_currency_history_from_cb(currency_code, period):
    """Получает исторические данные о курсах валют из ЦБ РФ."""
    import xml.etree.ElementTree as ET
    from datetime import datetime, timedelta
    
    today = datetime.now()
    
    # Определяем период для запроса
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    elif period == 'year':
        start_date = today - timedelta(days=365)
    else:  # day
        start_date = today - timedelta(days=1)
    
    # Форматируем даты для запроса
    date_format = "%d/%m/%Y"
    date1 = start_date.strftime(date_format)
    date2 = today.strftime(date_format)
    
    # URL для запроса курсов валют за период
    # Документация: http://www.cbr.ru/development/SXML/
    url = f"http://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date1}&date_req2={date2}&VAL_NM_RQ={get_cb_currency_code(currency_code)}"
    
    response = requests.get(url)
    response.raise_for_status()
    
    # Парсим XML
    root = ET.fromstring(response.content)
    result = []
    
    for record in root.findall('Record'):
        date_str = record.get('Date')
        value_str = record.find('Value').text.replace(',', '.')
        
        # Преобразуем дату из формата ЦБ в ISO
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        
        result.append({
            'date': date_obj.strftime("%Y-%m-%d"),
            'value': float(value_str)
        })
    
    return result


def get_cb_currency_code(currency_code):
    """Возвращает код валюты для API ЦБ РФ."""
    # Коды валют для API ЦБ
    # Полный список кодов: http://www.cbr.ru/scripts/XML_val.asp?d=0
    cb_codes = {
        'USD': 'R01235',  # Доллар США
        'EUR': 'R01239',  # Евро
        'CNY': 'R01375',  # Китайский юань
        'GBP': 'R01035'   # Фунт стерлингов
    }
    
    return cb_codes.get(currency_code, 'R01235')  # По умолчанию USD


def generate_test_currency_data(currency_code, period):
    """Генерирует тестовые данные для обычных валют."""
    from datetime import datetime, timedelta
    import random
    
    today = datetime.now()
    result = []
    
    # Базовые значения для разных валют
    base_values = {
        'USD': 90,
        'EUR': 100,
        'GBP': 115,
        'CNY': 12
    }
    
    base_value = base_values.get(currency_code, 90)
    
    # Определяем количество точек и временной шаг
    if period == 'day':
        days = 1
        points = 24
        delta = timedelta(hours=1)
        start_date = today - timedelta(days=days)
    elif period == 'week':
        days = 7
        points = days
        delta = timedelta(days=1)
        start_date = today - timedelta(days=days)
    elif period == 'month':
        days = 30
        points = days
        delta = timedelta(days=1)
        start_date = today - timedelta(days=days)
    else:  # year
        days = 365
        points = 12
        delta = timedelta(days=30)
        start_date = today - timedelta(days=days)
    
    # Создаем массив данных с некоторой волатильностью
    for i in range(points):
        date = start_date + delta * i
        volatility = base_value * 0.05  # 5% волатильность
        value = base_value + (random.random() - 0.5) * volatility
        
        result.append({
            'date': date.strftime("%Y-%m-%d"),
            'value': round(value, 2)
        })
    
    return result


def generate_test_crypto_data(currency_code, period):
    """Генерирует тестовые данные для криптовалют."""
    from datetime import datetime, timedelta
    import random
    
    today = datetime.now()
    result = []
    
    # Базовые значения для криптовалют
    base_values = {
        'BTC': 30000,
        'ETH': 1600
    }
    
    base_value = base_values.get(currency_code, 30000)
    
    # Определяем количество точек и временной шаг
    if period == 'day':
        days = 1
        points = 24
        delta = timedelta(hours=1)
        start_date = today - timedelta(days=days)
    elif period == 'week':
        days = 7
        points = days
        delta = timedelta(days=1)
        start_date = today - timedelta(days=days)
    elif period == 'month':
        days = 30
        points = days
        delta = timedelta(days=1)
        start_date = today - timedelta(days=days)
    else:  # year
        days = 365
        points = 12
        delta = timedelta(days=30)
        start_date = today - timedelta(days=days)
    
    # Создаем массив данных с некоторой волатильностью
    for i in range(points):
        date = start_date + delta * i
        volatility = base_value * 0.1  # 10% волатильность для крипты (больше, чем для обычных валют)
        value = base_value + (random.random() - 0.5) * volatility
        
        result.append({
            'date': date.strftime("%Y-%m-%d"),
            'value': round(value, 2)
        })
    
    return result


def weather_view(request):
    try:
        current_weather = weather_service.get_current_weather()
        forecast = weather_service.get_forecast()
        return render(request, 'weather.html', {
            'current_weather': current_weather,
            'forecast': forecast,
            'error': None
        })
    except ValueError as e:
        return render(request, 'weather.html', {
            'error': str(e)
        })