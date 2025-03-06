from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import redirect
from django.contrib import messages
from .models import News, NewsRating

def main(request):
    """Главная страница с новостями"""
    news_list = News.objects.all()
    return render(request, 'main.html', {'news_list': news_list})

def login_view(request):
    """Страница входа"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')
                return redirect('main')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def register_view(request):
    """Страница регистрации"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешно завершена!')
            return redirect('main')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из аккаунта.')
    return redirect('main')

@require_POST
def skip_news(request):
    """Обработка пропуска новости"""
    return JsonResponse({'status': 'success'})

@require_POST
@login_required
def rate_news(request):
    """Обработка оценки новости"""
    news_id = request.POST.get('news_id')
    rating_type = request.POST.get('rating_type')
    
    if news_id and rating_type in ['like', 'dislike']:
        news = get_object_or_404(News, id=news_id)
        
        # Проверяем, не оценивал ли пользователь эту новость ранее
        rating, created = NewsRating.objects.get_or_create(
            news=news,
            user=request.user,
            defaults={'rating_type': rating_type}
        )
        
        # Если оценка уже существует и не совпадает с текущей, обновляем её
        if not created and rating.rating_type != rating_type:
            rating.rating_type = rating_type
            rating.save()
        
        # Получаем количество лайков и дизлайков
        likes = NewsRating.objects.filter(news=news, rating_type='like').count()
        dislikes = NewsRating.objects.filter(news=news, rating_type='dislike').count()
        
        return JsonResponse({
            'status': 'success',
            'likes': likes,
            'dislikes': dislikes
        })
    
    return JsonResponse({'status': 'error', 'message': 'Неверные параметры'}, status=400)