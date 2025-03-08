from django.shortcuts import render, redirect, 
from django.utils.timezone import now
from .models import News, CurrencyRate, BackgroundImage, NewsRating, UserProfile


from itertools import cycle


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