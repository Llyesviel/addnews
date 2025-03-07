from django.urls import path, include, re_path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()

urlpatterns = [
    path('', views.redirect_to_main, name='index'),
    path('main/', views.main_page, name='main'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('api/', include(router.urls)),
    path('api/rate-news/', views.rate_news, name='rate_news'),
    path('api/skip-news/', views.skip_news, name='skip_news'),
    path('api/change-password/', views.change_password, name='change_password'),
    path('test-404/', views.test_404, name='test_404'),
    
    # Перенаправление всех остальных URL на test-404
    re_path(r'^.*$', views.redirect_to_404, name='catch_all'),
]