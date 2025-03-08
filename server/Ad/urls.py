from django.urls import path, include, re_path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()

urlpatterns = [
    # Добавляем маршрут для корневого URL
    path('', views.main_page, name='home'),
    path('main/', views.main_page, name='main'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('api/', include(router.urls)),
    path('api/rate-news/', views.rate_news, name='rate_news'),
    path('api/rate-news', views.rate_news),
    path('api/skip-news/', views.skip_news, name='skip_news'),
    path('api/skip-news', views.skip_news),
    path('api/change-password/', views.change_password, name='change_password'),
    path('api/comments/<int:news_id>/', views.get_comments, name='get_comments'),
    path('api/add-comment/', views.add_comment, name='add_comment'),
    path('test-404/', views.test_404, name='test_404'),
    
    # Временно отключаем перенаправление для отладки
    # re_path(r'^(?!main/|login/|register/|logout/|profile/|test-404/|api/rate-news|api/skip-news|api/change-password).*$', views.redirect_to_404, name='catch_all'),
]

# Добавляем специальный обработчик для 404 ошибок
handler404 = 'Ad.views.page_not_found'