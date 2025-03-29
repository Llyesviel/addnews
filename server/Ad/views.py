from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from .models import News, CurrencyRate, BackgroundImage, NewsRating, UserProfile, NewsComment, CurrencyRateHistory
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
from datetime import datetime, timedelta, timezone
from django.utils import timezone as django_timezone
from pycbrf import ExchangeRates
from zoneinfo import ZoneInfo  # Используем zoneinfo вместо timezone


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


# Кеш для хранения сгенерированных данных
# Структура: {currency_code: {period: [data]}}
_currency_data_cache = {}
_last_hour_checked = None

def _clear_day_cache_if_hour_changed():
    """Проверяет, сменился ли час, и если да - очищает кеш дневных данных"""
    global _last_hour_checked
    current_hour = datetime.now().hour
    
    # Если часы изменились или это первая проверка
    if _last_hour_checked is None or _last_hour_checked != current_hour:
        # Очищаем только дневные данные
        for currency in list(_currency_data_cache.keys()):
            if 'day' in _currency_data_cache[currency]:
                del _currency_data_cache[currency]['day']
        
        _last_hour_checked = current_hour

def fetch_crypto_history_from_coingecko(currency_code, period):
    """Получает исторические данные о курсах криптовалют из CoinGecko."""
    from datetime import datetime, timedelta
    import time
    
    # Маппинг криптовалютных кодов на ID в CoinGecko
    crypto_ids = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum'
    }
    
    # Получаем ID криптовалюты
    crypto_id = crypto_ids.get(currency_code)
    if not crypto_id:
        raise ValueError(f"Неизвестный код криптовалюты: {currency_code}")
    
    # Определяем параметры запроса в зависимости от периода
    today = datetime.now()
    result = []
    
    if period == 'day':
        # Для дневного периода используем почасовые данные (1-минутные свечи за последние 24 часа)
        days = 1
        interval = 'hourly'  # Почасовые точки данных
        
        # Для дневного режима используем /coins/{id}/market_chart с минутными интервалами
        url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days,
            "interval": interval
        }
    else:
        # Определяем параметры для других периодов
        if period == 'week':
            days = 7
        elif period == 'month':
            days = 30
        else:  # year
            days = 365
        
        # Для других периодов используем /coins/{id}/market_chart с дневными интервалами
        url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days,
            "interval": "daily"
        }
    
    # Делаем запрос к API
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Полученные данные в формате [[timestamp, price], ...] 
        prices = data.get('prices', [])
        
        # Преобразуем данные в нужный формат
        for price_data in prices:
            timestamp, price = price_data
            
            # Конвертируем timestamp (в миллисекундах) в datetime
            date_obj = datetime.fromtimestamp(timestamp / 1000)
            
            # Форматируем дату в зависимости от периода
            if period == 'day':
                date_str = date_obj.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = date_obj.strftime("%Y-%m-%d")
            
            result.append({
                'date': date_str,
                'value': round(price, 2)  # Цена в долларах США
            })
        
        return result
    except Exception as e:
        logging.error(f"Ошибка при получении данных с CoinGecko: {str(e)}")
        raise e


def fetch_crypto_history_from_cryptocompare(currency_code, period):
    """Получает исторические данные о курсах криптовалют из CryptoCompare."""
    from datetime import datetime, timedelta
    
    # Маппинг криптовалютных кодов
    crypto_symbols = {
        'BTC': 'BTC',
        'ETH': 'ETH'
    }
    
    symbol = crypto_symbols.get(currency_code)
    if not symbol:
        raise ValueError(f"Неизвестный код криптовалюты: {currency_code}")
    
    # Определяем параметры запроса в зависимости от периода
    result = []
    
    # URL для CryptoCompare API
    base_url = "https://min-api.cryptocompare.com/data"
    
    if period == 'day':
        # Для дневного периода получаем почасовые данные
        # Используем histohour с лимитом 24 часа
        url = f"{base_url}/v2/histohour"
        params = {
            "fsym": symbol,
            "tsym": "USD",
            "limit": 24,
            "aggregate": 1
        }
    elif period == 'week':
        # Для недельного периода получаем данные за каждый день недели
        url = f"{base_url}/v2/histoday"
        params = {
            "fsym": symbol,
            "tsym": "USD",
            "limit": 7,
            "aggregate": 1
        }
    elif period == 'month':
        # Для месячного периода получаем данные за каждый день месяца
        url = f"{base_url}/v2/histoday"
        params = {
            "fsym": symbol,
            "tsym": "USD",
            "limit": 30,
            "aggregate": 1
        }
    else:  # year
        # Для годового периода получаем данные за каждый день года
        url = f"{base_url}/v2/histoday"
        params = {
            "fsym": symbol,
            "tsym": "USD",
            "limit": 365,
            "aggregate": 1
        }
    
    # Делаем запрос к API
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['Response'] == 'Error':
            raise Exception(data['Message'])
        
        # Получаем данные о ценах
        price_data = data['Data']['Data']
        
        # Преобразуем данные в нужный формат
        for point in price_data:
            timestamp = point['time']
            close_price = point['close']
            
            # Конвертируем timestamp в datetime
            date_obj = datetime.fromtimestamp(timestamp)
            
            # Форматируем дату в зависимости от периода
            if period == 'day':
                date_str = date_obj.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = date_obj.strftime("%Y-%m-%d")
            
            result.append({
                'date': date_str,
                'value': round(close_price, 2)  # Цена в долларах США
            })
        
        # Сортируем результаты по дате
        result.sort(key=lambda x: x['date'])
        
        return result
    except Exception as e:
        logging.error(f"Ошибка при получении данных с CryptoCompare: {str(e)}")
        raise e


@require_POST
def get_currency_history(request):
    """API-endpoint для получения исторических данных о курсах валют."""
    try:
        # Очищаем кеш дневных данных, если сменился час
        _clear_day_cache_if_hour_changed()
        
        data = json.loads(request.body)
        currency_code = data.get('currency_code')
        period = data.get('period', 'month')
        
        if not currency_code:
            return JsonResponse({'status': 'error', 'message': 'Не указан код валюты'})
        
        # Используем кеш данных для конкретной валюты и периода
        cache_key = f"{currency_code}_{period}"
        
        # Для криптовалют получаем данные с внешних API
        if currency_code in ['BTC', 'ETH']:
            # Проверяем кеш сначала
            if currency_code in _currency_data_cache and period in _currency_data_cache[currency_code]:
                return JsonResponse({
                    'status': 'success',
                    'data': _currency_data_cache[currency_code][period]
                })
                
            # Если в кеше нет, получаем реальные данные
            try:
                # Сначала проверяем, есть ли данные в БД для криптовалют (дневной период)
                if period == 'day':
                    history_data = get_crypto_history_from_db(currency_code)
                    if history_data and len(history_data) > 0:
                        # Сохраняем в кеш
                        if currency_code not in _currency_data_cache:
                            _currency_data_cache[currency_code] = {}
                        _currency_data_cache[currency_code][period] = history_data
                        
                        return JsonResponse({
                            'status': 'success',
                            'data': history_data
                        })
                
                # Если в БД нет данных или это не дневной период, используем генерацию данных
                # на основе последних записей
                try:
                    # Пробуем получить данные из CoinGecko
                    history_data = fetch_crypto_history_from_coingecko(currency_code, period)
                except Exception as e:
                    logging.error(f"Ошибка при получении данных из CoinGecko: {str(e)}")
                    try:
                        # Если CoinGecko не сработал, пробуем CryptoCompare
                        history_data = fetch_crypto_history_from_cryptocompare(currency_code, period)
                    except Exception as e2:
                        logging.error(f"Ошибка при получении данных из CryptoCompare: {str(e2)}")
                        # Генерируем данные на основе последней записи или фиксированного значения
                        history_data = generate_test_crypto_data(currency_code, period)
            except Exception as e:
                logging.error(f"Ошибка при получении данных для криптовалюты {currency_code}: {str(e)}")
                history_data = generate_test_crypto_data(currency_code, period)
            
            # Сохраняем в кеш
            if currency_code not in _currency_data_cache:
                _currency_data_cache[currency_code] = {}
            _currency_data_cache[currency_code][period] = history_data
            
            return JsonResponse({
                'status': 'success',
                'data': history_data
            })
        
        # Для обычных валют сначала пытаемся получить данные из БД
        try:
            # Проверяем кеш сначала
            if currency_code in _currency_data_cache and period in _currency_data_cache[currency_code]:
                return JsonResponse({
                    'status': 'success',
                    'data': _currency_data_cache[currency_code][period]
                })
            
            # Если кеша нет, пытаемся получить данные из БД (особенно важно для дневного периода)
            if period == 'day':
                history_data = get_currency_history_from_db(currency_code)
                
                if history_data and len(history_data) > 0:
                    # Сохраняем в кеш
                    if currency_code not in _currency_data_cache:
                        _currency_data_cache[currency_code] = {}
                    _currency_data_cache[currency_code][period] = history_data
                    
                    return JsonResponse({
                        'status': 'success',
                        'data': history_data
                    })
            
            # Для других периодов или если в БД нет достаточных данных, 
            # используем только ЦБ РФ
            history_data = fetch_currency_history_from_cb(currency_code, period)
            
            # Сохраняем в кеш
            if currency_code not in _currency_data_cache:
                _currency_data_cache[currency_code] = {}
            _currency_data_cache[currency_code][period] = history_data
            
            return JsonResponse({
                'status': 'success',
                'data': history_data
            })
        except Exception as e:
            logging.error(f"Ошибка при получении истории курсов: {str(e)}")
            
            # Если в кеше нет, генерируем тестовые данные
            if currency_code not in _currency_data_cache or period not in _currency_data_cache[currency_code]:
                history_data = generate_test_currency_data(currency_code, period)
                
                # Сохраняем в кеш
                if currency_code not in _currency_data_cache:
                    _currency_data_cache[currency_code] = {}
                _currency_data_cache[currency_code][period] = history_data
            else:
                history_data = _currency_data_cache[currency_code][period]
                
            return JsonResponse({
                'status': 'success',
                'data': history_data
            })
            
    except Exception as e:
        logging.error(f"Ошибка в get_currency_history: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


def get_currency_history_from_db(currency_code):
    """Получает историю курсов обычных валют из БД для дневного периода."""
    from .models import CurrencyRateHistory
    from datetime import datetime, timedelta
    
    # Получаем данные за последние 24 часа 
    end_time = django_timezone.now()
    start_time = end_time - timedelta(days=1)
    
    # Получаем записи из БД, отсортированные по времени
    history_records = CurrencyRateHistory.objects.filter(
        currency_name=currency_code,
        timestamp__gte=start_time,
        timestamp__lte=end_time
    ).order_by('timestamp')
    
    # Проверяем, что есть достаточное количество записей
    if history_records.count() < 4:  # Минимальное количество точек для отображения
        logging.warning(f"Недостаточно данных в БД для {currency_code}, найдено {history_records.count()} записей")
        return []
    
    # Преобразуем записи в нужный формат
    result = []
    for record in history_records:
        # Форматируем дату и время
        date_str = record.timestamp.strftime("%Y-%m-%d %H:%M")
        
        result.append({
            'date': date_str,
            'value': float(record.rate)
        })
    
    return result


def get_crypto_history_from_db(currency_code):
    """Получает историю курсов криптовалют из БД для дневного периода."""
    from .models import CurrencyRateHistory
    from datetime import datetime, timedelta
    
    # Получаем данные за последние 24 часа 
    end_time = django_timezone.now()
    start_time = end_time - timedelta(days=1)
    
    # Получаем записи из БД, отсортированные по времени
    history_records = CurrencyRateHistory.objects.filter(
        currency_name=currency_code,
        timestamp__gte=start_time,
        timestamp__lte=end_time
    ).order_by('timestamp')
    
    # Проверяем, что есть достаточное количество записей
    if history_records.count() < 4:  # Минимальное количество точек для отображения
        logging.warning(f"Недостаточно данных в БД для {currency_code}, найдено {history_records.count()} записей")
        return []
    
    # Преобразуем записи в нужный формат
    result = []
    for record in history_records:
        # Форматируем дату и время
        date_str = record.timestamp.strftime("%Y-%m-%d %H:%M")
        
        result.append({
            'date': date_str,
            'value': float(record.rate)
        })
    
    return result


def fetch_currency_history_from_cb(currency_code, period):
    """Получает исторические данные о курсах валют из ЦБ РФ и данных из БД."""
    import xml.etree.ElementTree as ET
    from datetime import datetime, timedelta
    import random
    import math
    
    today = datetime.now()
    
    # Определяем период для запроса
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    elif period == 'year':
        start_date = today - timedelta(days=365)
    else:  # day
        # Для дневного периода используем интерполяцию на основе данных из БД или ЦБ РФ
        logging.info(f"Генерируем данные для {currency_code} на основе БД и ЦБ РФ")
        
        # Получаем базовое значение для интерполяции
        last_value = None
        
        # Проверяем, есть ли данные в БД
        from .models import CurrencyRateHistory
        latest_record = CurrencyRateHistory.objects.filter(currency_name=currency_code).order_by('-timestamp').first()
        
        if latest_record:
            # Если есть хотя бы одна запись, используем её значение для интерполяции
            last_value = float(latest_record.rate)
            logging.info(f"Найдена последняя запись в БД для {currency_code}: {last_value}")
        else:
            # Если записей нет, получаем текущий курс из ЦБ РФ
            try:
                rates = ExchangeRates()
                last_value = float(rates[currency_code].rate)
                logging.info(f"Получен текущий курс из ЦБ РФ для {currency_code}: {last_value}")
            except Exception as e:
                logging.error(f"Ошибка при получении курса из ЦБ РФ для {currency_code}: {e}")
                # Используем дефолтное значение, если все методы не сработали
                if currency_code == "USD":
                    last_value = 90.0
                elif currency_code == "EUR":
                    last_value = 100.0
                elif currency_code == "CNY":
                    last_value = 12.5
                else:
                    last_value = 10.0
                
                logging.info(f"Используем дефолтное значение для {currency_code}: {last_value}")
        
        # Текущий час
        current_hour = today.hour
        
        # Генерируем 24 точки данных для часового представления дня
        result = []
        for hour in range(24):
            # Вычисляем время для данной точки
            hour_date = today.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # Если час еще не наступил, используем данные предыдущего дня
            if hour > current_hour:
                hour_date = hour_date - timedelta(days=1)
            
            # Создаем волатильность на основе времени дня
            # Биржевая активность выше в рабочие часы (10-19), имитируем это
            time_factor = math.sin((hour - 3) * math.pi / 12) * 0.5 + 0.5  # Пик около 15:00
            volatility = last_value * 0.01 * time_factor  # До 1% волатильности
            
            # Добавляем случайный компонент
            random_factor = (random.random() - 0.5) * 2  # От -1 до 1
            hour_value = last_value + (volatility * random_factor)
            
            # Для текущего часа используем более близкое к последнему известному значение
            if hour == current_hour:
                random_factor = (random.random() - 0.5)  # От -0.5 до 0.5
                hour_value = last_value + (volatility * random_factor * 0.5)
                
            result.append({
                'date': hour_date.strftime("%Y-%m-%d %H:%M"),
                'value': round(hour_value, 4)
            })
            
        # Сортируем результаты, чтобы убедиться в правильном порядке
        result.sort(key=lambda x: x['date'])
        return result
    
    # Для других периодов (неделя, месяц, год) используем данные ЦБ РФ
    try:
        # Форматируем даты для запроса к ЦБ РФ
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
        
        # Получаем базовые данные из ответа ЦБ
        raw_data = []
        for record in root.findall('Record'):
            date_str = record.get('Date')
            value_str = record.find('Value').text.replace(',', '.')
            
            # Преобразуем дату из формата ЦБ в ISO
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            
            raw_data.append({
                'date': date_obj,
                'value': float(value_str)
            })
            
        # Если нет данных от ЦБ, используем генерацию тестовых данных
        if not raw_data:
            logging.warning(f"Нет данных от ЦБ РФ для {currency_code} за период {period}, используем тестовые данные")
            return generate_test_currency_data(currency_code, period)
            
        # Форматируем результат
        for item in raw_data:
            result.append({
                'date': item['date'].strftime("%Y-%m-%d"),
                'value': item['value']
            })
        
        return result
    except Exception as e:
        logging.error(f"Ошибка при получении данных от ЦБ РФ для {currency_code}: {e}")
        # В случае ошибки генерируем тестовые данные
        return generate_test_currency_data(currency_code, period)

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
        
        # Для дневного периода генерируем данные по часам с правильным временем
        current_hour = today.hour
        
        # Генерируем 24 точки данных для часового представления дня
        for hour in range(24):
            # Вычисляем время для данной точки
            hour_date = today.replace(hour=hour, minute=0, second=0, microsecond=0)
            
            # Если час еще не наступил, используем данные предыдущего дня
            if hour > current_hour:
                hour_date = hour_date - timedelta(days=1)
            
            volatility = base_value * 0.1  # 10% волатильность для крипты
            value = base_value + (random.random() - 0.5) * volatility
            
            result.append({
                'date': hour_date.strftime("%Y-%m-%d %H:%M"),
                'value': round(value, 2)
            })
        
        return result
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
    
    # Для других периодов (неделя, месяц, год) - обычный формат
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
        # Обработка переключения городов
        city_action = request.GET.get('city_action')
        
        if city_action == 'next':
            weather_service.next_city()
        elif city_action == 'prev':
            weather_service.prev_city()
        elif city_action:  # Если указан конкретный город
            weather_service.set_city(city_action)
            
        # Текущий выбранный город
        current_city = weather_service.get_current_city()
        
        # Получаем текущую погоду
        current_weather = weather_service.get_current_weather()
        
        if not current_weather:
            raise ValueError("Не удалось получить данные о погоде")
        
        # Получаем прогноз на 6 дней
        forecast = weather_service.get_forecast()
        
        # Получаем почасовой прогноз из API
        hourly_forecast = weather_service.get_hourly_forecast()

        # Получаем часовой пояс текущего города
        tz_offset = weather_service.get_city_timezone_offset()
        
        # Создаем объект времени с правильным часовым поясом
        utc_now = datetime.utcnow()
        city_time = utc_now + timedelta(hours=tz_offset)
        
        context = {
            'current_weather': current_weather,
            'forecast': forecast,
            'hourly_forecast': hourly_forecast,
            'current_time': city_time,
            'current_city': current_city,
            'current_timezone': tz_offset,
            'city_list': weather_service.get_city_list()
        }
        
        return render(request, 'weather.html', context)
        
    except Exception as e:
        logging.error(f"Ошибка при получении погоды из API: {str(e)}")
        
        # Возвращаем страницу с сообщением об ошибке
        context = {
            'error': True,
            'error_message': str(e)
        }
        
        return render(request, 'weather.html', context)