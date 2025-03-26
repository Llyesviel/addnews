from django.urls import path, include, re_path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()

# Группируем все API-маршруты в отдельный модуль
api_patterns = [
    path('', include(router.urls)),
    path('rate-news/', views.rate_news, name='rate_news'),
    path('rate-news', views.rate_news),
    path('skip-news/', views.skip_news, name='skip_news'),
    path('skip-news', views.skip_news),
    path('change-password/', views.change_password, name='change_password'),
    path('comments/<int:news_id>/', views.get_comments, name='get_comments'),
    path('add-comment/', views.add_comment, name='add_comment'),
    path('currency-history/', views.get_currency_history, name='currency_history'),
]

# Явно указываем основные маршруты приложения
main_patterns = [
    path('', views.main_page, name='home'),
    path('main/', views.main_page, name='main'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('currency/', views.currency_charts, name='currency_charts'),
    path('weather/', views.weather_view, name='weather'),
    path('test-404/', views.test_404, name='test_404'),
]

urlpatterns = [
    # Основные маршруты
    *main_patterns,
    
    # API-маршруты
    path('api/', include(api_patterns)),
    
    # Перенаправление остальных URL на страницу 404
    # Исключая маршруты, начинающиеся с 'admin'
    path('calendar/<int:year>/<int:month>/', views.get_calendar, name='get_calendar'),
    re_path(r'^(?!admin).*$', views.redirect_to_404, name='catch_all'),
]

# Обработчик для 404 ошибок
handler404 = 'Ad.views.page_not_found'