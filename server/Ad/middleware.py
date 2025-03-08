from django.http import Http404
from django.shortcuts import render
import logging

class Custom404Middleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('Ad.middleware')

    def __call__(self, request):
        response = self.get_response(request)
        
        # Если API-запрос, не перехватываем его
        if request.path.startswith('/api/'):
            self.logger.debug(f"Skipping middleware for API request: {request.path}")
            return response
            
        if response.status_code == 404 and not response.content:
            self.logger.debug(f"Middleware handling 404 for: {request.path}")
            from .models import CurrencyRate
            currency_rates = CurrencyRate.objects.all()
            return render(request, '404.html', {
                'currency_rates': currency_rates
            }, status=404)
        return response 