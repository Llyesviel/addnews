from django.http import Http404
from django.shortcuts import render
import logging
import re

class Custom404Middleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('Ad.middleware')
        # Компилируем регулярное выражение для лучшей производительности
        self.api_pattern = re.compile(r'^/api/')

    def __call__(self, request):
        # Проверка на API-запрос до выполнения основного запроса
        if self.api_pattern.match(request.path):
            self.logger.debug(f"API запрос обнаружен, пропускаем middleware: {request.path}")
            return self.get_response(request)
            
        # Обрабатываем запрос
        response = self.get_response(request)
        
        # Проверяем ответ только для не-API запросов
        if response.status_code == 404 and not response.content:
            self.logger.debug(f"Middleware обрабатывает 404 для: {request.path}")
            from .models import CurrencyRate
            currency_rates = CurrencyRate.objects.all()
            return render(request, '404.html', {
                'currency_rates': currency_rates
            }, status=404)
            
        return response 