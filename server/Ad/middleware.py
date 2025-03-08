from django.http import Http404
from django.shortcuts import render

class Custom404Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404 and not response.content:
            from .models import CurrencyRate
            currency_rates = CurrencyRate.objects.all()
            return render(request, '404.html', {
                'currency_rates': currency_rates
            }, status=404)
        return response 