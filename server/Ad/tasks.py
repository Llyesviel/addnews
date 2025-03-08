from .models import CurrencyRate, News, NewsSource
from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
import logging
from pycbrf import ExchangeRates
import requests
from decimal import Decimal
import feedparser
from datetime import timedelta
from datetime import datetime
from django.utils.html import strip_tags
import re

class SchedulerSingleton:
    _instance = None
    logger = logging.getLogger(__name__)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._initialize_scheduler()
        return cls._instance

    # Инициализация планировщика - Метод _initialize_scheduler:
    # Данный метод создает и настраивает планировщик фоновых задач на основе библиотеки apscheduler.
    # Он регистрирует все периодические задачи приложения с указанием интервалов их выполнения:
    # - Обновление курсов валют (ежедневно в полночь)
    # - Сбор новостей (каждые 6 часов)
    # Также планировщик выполняет начальный запуск задач при старте приложения.
    @classmethod
    def _initialize_scheduler(cls):
        cls._scheduler = BackgroundScheduler()
        cls._scheduler.add_job(cls.update_currency_job, 'cron', hour=0, minute=0, id='update_currency_job', replace_existing=True)
        cls._scheduler.add_job(cls.fetch_news, 'interval', hours=6, id='fetch_news', replace_existing=True)
        cls._scheduler.add_job(cls.update_currency_job, 'date', run_date=timezone.now(), id='update_currency_job_init', replace_existing=True)
        cls._scheduler.add_job(cls.fetch_news, 'date', run_date=timezone.now() + timedelta(seconds=5), id='fetch_news_init', replace_existing=True)
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
            
    @classmethod
    def FEED_URLS(cls):
        active_sources = NewsSource.objects.filter(is_active=True)
        return {source.name: source.feed_url for source in active_sources}

    @classmethod
    def fetch_news(cls):
        try:
            feed_urls = cls.FEED_URLS()
            for feed_name, feed_url in feed_urls.items():
                feed = feedparser.parse(feed_url)
                entries = feed.entries
                for entry in entries:
                    title = entry.get("title", "Без заголовка")
                    description = strip_tags(entry.get("description", ""))
                    description = description.replace('&nbsp;', ' ')
                    description = description.replace('&ndash;', '-')
                    description = cls.limit_description(description, 3)
                    published_at = entry.get("published", "")
                    link = entry.get("link", "")
                    # Извлечение изображения из описания, если доступно
                    image_url = ""
                    if '<img src="' in description:
                        start = description.find('<img src="') + len('<img src="')
                        end = description.find('"', start)
                        image_url = description[start:end] if end > start else ""
                    
                    # Преобразуем дату публикации в объект datetime
                    if published_at:
                        try:
                            date_published = datetime.strptime(published_at, "%a, %d %b %Y %H:%M:%S %z")
                        except ValueError:
                            date_published = timezone.now()
                    else:
                        date_published = timezone.now()

                    # Фильтрация новостей по ключевым словам для обеспечения финансовой тематики
                    allowed_keywords = [
                        'финанс', 'эконом', 'кредит', 'валюта', 'цб', 'банк',
                        'акции', 'биржа', 'инвестиции', 'депозит', 'монета',
                        'финансовый', 'прибыль', 'налоги', 'рынок', 'удорожение',
                        'спред', 'коммерция', 'банкротство', 'валютный', 'инфляция',
                        'ставка', 'оверрайт', 'рынок капитала', 'кредитование'
                    ]
                    if not any(keyword in title.lower() or keyword in description.lower() for keyword in allowed_keywords):
                        continue

                    # Проверка, что новость опубликована в последние 96 часов
                    ninety_six_hours_ago = timezone.now() - timedelta(hours=96)
                    if date_published < ninety_six_hours_ago:
                        continue

                    # Получаем источник по названию RSS канала
                    try:
                        source = NewsSource.objects.get(name=feed_name)
                    except NewsSource.DoesNotExist:
                        source = None

                    News.objects.update_or_create(
                        link=link,
                        defaults={
                            'title': title,
                            'description': description,
                            'date_published': date_published,
                            'image': image_url,
                            'source': source
                        }
                    )
            
            # Удаляем новости старше 96 часов
            ninety_six_hours_ago = timezone.now() - timedelta(hours=96)
            News.objects.filter(date_published__lt=ninety_six_hours_ago).delete()
            
            cls.logger.info("Парсинг новостей завершен успешно.")
        except Exception as e:
            cls.logger.error(f"Ошибка при получении новостей через RSS: {e}")

    @classmethod
    def limit_description(cls, text, num_sentences=3):
        """
        Ограничивает количество предложений в тексте до указанного числа.
        """
        # Добавляем пробелы после знаков препинания, если их нет
        text = re.sub(r'(?<=[.!?])(?=\S)', r'\g<0> ', text)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return ' '.join(sentences[:num_sentences]) if len(sentences) > num_sentences else text

    # Выборочное обновление новостей - Метод fetch_news_from_sources
    # Данный метод позволяет обновлять новости только из указанных источников,
    # в отличие от основного метода fetch_news, который обрабатывает все активные источники.
    # Это полезно для ручного обновления определенных источников или тестирования новых RSS-каналов.
    @classmethod
    def fetch_news_from_sources(cls, sources):
        """
        Обновляет новости только из указанных источников
        """
        try:
            feed_urls = {source.name: source.feed_url for source in sources}
            for feed_name, feed_url in feed_urls.items():
                feed = feedparser.parse(feed_url)
                entries = feed.entries
                for entry in entries:
                    title = entry.get("title", "Без заголовка")
                    description = strip_tags(entry.get("description", ""))
                    description = description.replace('&nbsp;', ' ')
                    description = description.replace('&ndash;', '-')
                    description = cls.limit_description(description, 3)
                    published_at = entry.get("published", "")
                    link = entry.get("link", "")
                    
                    # Преобразуем дату публикации в объект datetime
                    if published_at:
                        try:
                            date_published = datetime.strptime(published_at, "%a, %d %b %Y %H:%M:%S %z")
                        except ValueError:
                            date_published = timezone.now()
                    else:
                        date_published = timezone.now()

                    # Фильтрация новостей по ключевым словам для обеспечения финансовой тематики
                    allowed_keywords = [
                        'финанс', 'эконом', 'кредит', 'валюта', 'цб', 'банк',
                        'акции', 'биржа', 'инвестиции', 'депозит', 'монета',
                        'финансовый', 'прибыль', 'налоги', 'рынок', 'удорожение',
                        'спред', 'коммерция', 'банкротство', 'валютный', 'инфляция',
                        'ставка', 'оверрайт', 'рынок капитала', 'кредитование'
                    ]
                    if not any(keyword in title.lower() or keyword in description.lower() for keyword in allowed_keywords):
                        continue

                    # Проверка, что новость опубликована в последние 96 часов
                    ninety_six_hours_ago = timezone.now() - timedelta(hours=96)
                    if date_published < ninety_six_hours_ago:
                        continue

                    # Получаем источник по названию RSS канала
                    try:
                        source = NewsSource.objects.get(name=feed_name)
                    except NewsSource.DoesNotExist:
                        source = None

                    News.objects.update_or_create(
                        link=link,
                        defaults={
                            'title': title,
                            'description': description,
                            'date_published': date_published,
                            'source': source
                        }
                    )
            
            cls.logger.info(f"Парсинг новостей из выбранных источников завершен успешно.")
        except Exception as e:
            cls.logger.error(f"Ошибка при получении новостей через RSS: {e}") 