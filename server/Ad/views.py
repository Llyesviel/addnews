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
    return render(request, 'profile.html', {'user': request.user})


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
    return JsonResponse({'status': 'success'})


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
    Функция для тестирования страницы 404 при включенном DEBUG режиме
    """
    from .models import CurrencyRate
    currency_rates = CurrencyRate.objects.all()

    return render(request, '404.html', {
        'currency_rates': currency_rates
    })


def redirect_to_404(request):
    """
    Функция перенаправления всех несуществующих URL на страницу test-404
    """
    logger = logging.getLogger('Ad.views')
    logger.debug(f"redirect_to_404 called for path: {request.path}")
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

