from .models import CurrencyRate
from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
import logging
from pycbrf import ExchangeRates
import requests
from decimal import Decimal

class SchedulerSingleton:
    _instance = None
    logger = logging.getLogger(__name__)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._initialize_scheduler()
        return cls._instance

    @classmethod
    def _initialize_scheduler(cls):
        cls._scheduler = BackgroundScheduler()
        cls._scheduler.add_job(cls.update_currency_job, 'cron', hour=0, minute=0, id='update_currency_job', replace_existing=True)
        cls._scheduler.add_job(cls.update_currency_job, 'date', run_date=timezone.now(), id='update_currency_job_init', replace_existing=True)
        cls._scheduler.start()

    @classmethod
    def get_crypto_rates(cls):
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin,ethereum",
                "vs_currencies": "usd"
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                "BTC": Decimal(str(data["bitcoin"]["usd"])),
                "ETH": Decimal(str(data["ethereum"]["usd"]))
            }
        except Exception as e:
            cls.logger.error(f"Ошибка при получении курсов криптовалют: {e}")
            return {}

    @classmethod
    def update_currency_job(cls):
        try:
            rates = ExchangeRates()
            
            currency_symbols = {
                "USD": "$",
                "EUR": "€",
                "CNY": "¥",
                "BTC": "₿",
                "ETH": "Ξ"
            }

            crypto_rates = cls.get_crypto_rates()

            for currency in ["USD", "EUR", "CNY"]:
                rate = rates[currency].rate
                CurrencyRate.objects.update_or_create(
                    currency_name=currency,
                    defaults={
                        'rate': rate,
                        'symbol': currency_symbols[currency]
                    }
                )

            for crypto, rate in crypto_rates.items():
                CurrencyRate.objects.update_or_create(
                    currency_name=crypto,
                    defaults={
                        'rate': rate,
                        'symbol': currency_symbols[crypto]
                    }
                )

            cls.logger.info(f"Курсы валют обновлены в: {timezone.now()}")
        except Exception as e:
            cls.logger.error(f"Ошибка при обновлении курсов валют: {e}") 