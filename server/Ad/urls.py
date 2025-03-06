from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='main'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('skip-news/', views.skip_news, name='skip_news'),
    path('rate-news/', views.rate_news, name='rate_news'),
]