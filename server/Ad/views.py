from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from .models import News, CurrencyRate, BackgroundImage, NewsRating, UserProfile
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from itertools import cycle
from django.urls import reverse



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
        
        # Проверяем, оценил ли текущий пользователь эту новость
        if request.user.is_authenticated:
            try:
                rating = NewsRating.objects.get(news=news, user=request.user)
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


@login_required
@require_POST
def rate_news(request):
    news_id = request.POST.get('news_id')
    rating_type = request.POST.get('rating_type')  # 'like' или 'dislike'

    news = get_object_or_404(News, id=news_id)

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