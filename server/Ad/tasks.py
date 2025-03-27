from .models import CurrencyRate, News, NewsSource, CurrencyRateHistory
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
        cls._scheduler.add_job(cls.update_currency_job, 'interval', hours=1, id='update_currency_job', replace_existing=True)
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
            cls.logger.info(f"Запрос к CoinGecko API: {url} с параметрами {params}")
            
            response = requests.get(url, params=params, timeout=10)
            cls.logger.info(f"Статус ответа CoinGecko: {response.status_code}")
            
            if response.status_code != 200:
                cls.logger.error(f"Ошибка API CoinGecko. Статус: {response.status_code}, Ответ: {response.text}")
                # Возвращаем фиксированные значения при ошибке
                return {
                    "BTC": Decimal('30000.0000'),
                    "ETH": Decimal('1600.0000')
                }
            
            response.raise_for_status()
            data = response.json()
            
            # Проверяем структуру ответа
            if "bitcoin" not in data or "ethereum" not in data:
                cls.logger.error(f"Неверная структура ответа от CoinGecko: {data}")
                # Возвращаем фиксированные значения при ошибке
                return {
                    "BTC": Decimal('30000.0000'),
                    "ETH": Decimal('1600.0000')
                }
            
            result = {
                "BTC": Decimal(str(data["bitcoin"]["usd"])),
                "ETH": Decimal(str(data["ethereum"]["usd"]))
            }
            
            cls.logger.info(f"Получены курсы криптовалют от CoinGecko: {result}")
            return result
        except requests.exceptions.RequestException as e:
            cls.logger.error(f"Ошибка соединения с CoinGecko: {e}")
            # Возвращаем фиксированные значения при ошибке
            return {
                "BTC": Decimal('30000.0000'),
                "ETH": Decimal('1600.0000')
            }
        except Exception as e:
            cls.logger.error(f"Ошибка при получении курсов криптовалют: {e}")
            # Возвращаем фиксированные значения при ошибке
            return {
                "BTC": Decimal('30000.0000'),
                "ETH": Decimal('1600.0000')
            }

    @classmethod
    def update_currency_job(cls):
        try:
            # Очищаем кеш данных курсов валют при обновлении
            # Импортируем здесь, чтобы избежать цикличного импорта
            from .views import _currency_data_cache
            _currency_data_cache.clear()
            
            now = timezone.now()
            
            # Ограничиваем обновление только в ровное время часа - ПОЛНОСТЬЮ ОТКЛЮЧАЕМ
            # if now.minute != 0:
            #     cls.logger.info(f"Пропуск обновления курсов валют. Обновление только в начале часа (текущие минуты: {now.minute})")
            #     return
            
            cls.logger.info(f"Начало обновления курсов валют в {now}")
            
            currency_symbols = {
                "USD": "$",
                "EUR": "€",
                "CNY": "¥",
                "BTC": "₿",
                "ETH": "Ξ"
            }

            # Получаем курсы традиционных валют через OpenExchangeRates API
            forex_rates = cls.get_forex_rates_from_openexchangerates()
            cls.logger.info(f"Результат запроса к OpenExchangeRates: {forex_rates}")
            
            # Если не удалось получить данные от OpenExchangeRates, используем ЦБ РФ
            if not forex_rates:
                cls.logger.warning("Не удалось получить данные от OpenExchangeRates, используем ЦБ РФ")
                try:
                    rates = ExchangeRates()
                    for currency in ["USD", "EUR", "CNY"]:
                        rate = rates[currency].rate
                        # Обновляем текущий курс
                        CurrencyRate.objects.update_or_create(
                            currency_name=currency,
                            defaults={
                                'rate': rate,
                                'symbol': currency_symbols[currency],
                                'updated_at': now,
                                'source': 'ЦБ РФ'
                            }
                        )
                        
                        # Сохраняем историю курса
                        CurrencyRateHistory.objects.create(
                            currency_name=currency,
                            rate=rate,
                            timestamp=now,
                            source='ЦБ РФ'
                        )
                    cls.logger.info("Курсы традиционных валют успешно обновлены из ЦБ РФ")
                except Exception as e:
                    cls.logger.error(f"Ошибка при получении курсов валют через ЦБ РФ: {e}")
                    # Создаем фиксированные значения для отладки
                    cls.logger.warning("Создаем фиксированные значения для валют")
                    for currency, default_rate in {"USD": 90.0, "EUR": 100.0, "CNY": 12.5}.items():
                        try:
                            CurrencyRate.objects.update_or_create(
                                currency_name=currency,
                                defaults={
                                    'rate': default_rate,
                                    'symbol': currency_symbols[currency],
                                    'updated_at': now,
                                    'source': 'Фиксированное значение'
                                }
                            )
                            
                            # Сохраняем историю курса
                            CurrencyRateHistory.objects.create(
                                currency_name=currency,
                                rate=default_rate,
                                timestamp=now,
                                source='Фиксированное значение'
                            )
                        except Exception as inner_e:
                            cls.logger.error(f"Ошибка при создании фиксированного значения для {currency}: {inner_e}")
                    return
            else:
                # Обновляем курсы из OpenExchangeRates
                for currency, rate_info in forex_rates.items():
                    if currency in currency_symbols:
                        rate = rate_info['rate']
                        # Обновляем текущий курс
                        CurrencyRate.objects.update_or_create(
                            currency_name=currency,
                            defaults={
                                'rate': rate,
                                'symbol': currency_symbols[currency],
                                'updated_at': now,
                                'source': 'OpenExchangeRates'
                            }
                        )
                        
                        # Сохраняем историю курса
                        CurrencyRateHistory.objects.create(
                            currency_name=currency, 
                            rate=rate,
                            timestamp=now,
                            source='OpenExchangeRates'
                        )
                cls.logger.info("Курсы традиционных валют успешно обновлены из OpenExchangeRates")

            # Пробуем получить криптовалютные курсы
            crypto_rates = cls.get_crypto_rates()
            cls.logger.info(f"Результат запроса криптовалютных курсов: {crypto_rates}")
            
            # Обновляем криптовалюты
            for crypto, rate in crypto_rates.items():
                # Обновляем текущий курс
                CurrencyRate.objects.update_or_create(
                    currency_name=crypto,
                    defaults={
                        'rate': rate,
                        'symbol': currency_symbols[crypto],
                        'updated_at': now,
                        'source': 'CoinGecko'
                    }
                )
                
                # Сохраняем историю курса
                CurrencyRateHistory.objects.create(
                    currency_name=crypto,
                    rate=rate,
                    timestamp=now,
                    source='CoinGecko'
                )
            cls.logger.info("Курсы криптовалют успешно обновлены")

            # Очищаем историю старше 30 дней для экономии места
            thirty_days_ago = now - timedelta(days=30)
            old_records = CurrencyRateHistory.objects.filter(timestamp__lt=thirty_days_ago)
            deleted_count = old_records.count()
            old_records.delete()
            if deleted_count > 0:
                cls.logger.info(f"Удалено {deleted_count} устаревших записей истории курсов валют")

            cls.logger.info(f"Курсы валют обновлены в: {now}")
        except Exception as e:
            cls.logger.error(f"Ошибка при обновлении курсов валют: {e}")

    @classmethod
    def get_forex_rates_from_openexchangerates(cls):
        """
        Получает курсы валют через API OpenExchangeRates
        """
        try:
            app_id = "e3161d6ea05549ec8877326eeb64ad2e"  # API ключ
            cls.logger.info(f"Запрос к OpenExchangeRates API с ключом: {app_id}")
            
            url = f"https://openexchangerates.org/api/latest.json?app_id={app_id}&base=USD"
            cls.logger.info(f"URL запроса: {url}")
            
            response = requests.get(url, timeout=10)
            cls.logger.info(f"Статус ответа: {response.status_code}")
            
            if response.status_code != 200:
                cls.logger.error(f"Ошибка API OpenExchangeRates. Статус: {response.status_code}, Ответ: {response.text}")
                return {}
            
            response.raise_for_status()
            data = response.json()
            
            # Логируем структуру ответа для отладки
            cls.logger.info(f"Структура ответа: {data.keys()}")
            
            if 'rates' not in data:
                cls.logger.error(f"В ответе OpenExchangeRates нет данных о курсах: {data}")
                return {}
            
            # Получаем курс USD к RUB для конвертации
            if 'RUB' not in data['rates']:
                cls.logger.error("В ответе OpenExchangeRates нет данных о курсе RUB")
                return {}
            
            usd_to_rub = Decimal(str(data['rates']['RUB']))
            cls.logger.info(f"Курс USD к RUB: {usd_to_rub}")
            
            result = {}
            # Вычисляем курсы валют к рублю
            for currency in ["USD", "EUR", "CNY"]:
                if currency in data['rates']:
                    if currency == "USD":
                        # USD к RUB напрямую
                        rate = usd_to_rub
                    else:
                        # Для других валют конвертируем через USD
                        currency_to_usd = Decimal(str(data['rates'][currency]))
                        rate = usd_to_rub / currency_to_usd
                    
                    # Округляем до 4 знаков после запятой
                    result[currency] = {
                        'rate': rate.quantize(Decimal('0.0001')),
                        'timestamp': data.get('timestamp', 0)
                    }
                    cls.logger.info(f"Рассчитанный курс {currency} к RUB: {rate}")
                else:
                    cls.logger.warning(f"Валюта {currency} отсутствует в ответе API")
            
            cls.logger.info(f"Получены курсы валют от OpenExchangeRates: {result}")
            return result
        except requests.exceptions.RequestException as e:
            cls.logger.error(f"Ошибка соединения с OpenExchangeRates: {e}")
            return {}
        except ValueError as e:
            cls.logger.error(f"Ошибка при парсинге ответа от OpenExchangeRates: {e}")
            return {}
        except Exception as e:
            cls.logger.error(f"Ошибка при получении курсов валют от OpenExchangeRates: {e}")
            return {}

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

    @classmethod
    def update_currency_job_force(cls):
        """
        Принудительное обновление курсов валют (без проверки времени)
        Используется для ручного обновления из админ-панели
        """
        try:
            # Очищаем кеш данных курсов валют при обновлении
            # Импортируем здесь, чтобы избежать цикличного импорта
            from .views import _currency_data_cache
            _currency_data_cache.clear()
            
            now = timezone.now()
            cls.logger.info(f"Запущено принудительное обновление курсов валют в {now}")
            
            currency_symbols = {
                "USD": "$",
                "EUR": "€",
                "CNY": "¥",
                "BTC": "₿",
                "ETH": "Ξ"
            }

            # Получаем курсы традиционных валют через OpenExchangeRates API
            forex_rates = cls.get_forex_rates_from_openexchangerates()
            cls.logger.info(f"Результат запроса к OpenExchangeRates (force): {forex_rates}")
            
            # Если не удалось получить данные от OpenExchangeRates, используем ЦБ РФ
            if not forex_rates:
                cls.logger.warning("Не удалось получить данные от OpenExchangeRates, используем ЦБ РФ")
                try:
                    rates = ExchangeRates()
                    for currency in ["USD", "EUR", "CNY"]:
                        rate = rates[currency].rate
                        # Обновляем текущий курс
                        CurrencyRate.objects.update_or_create(
                            currency_name=currency,
                            defaults={
                                'rate': rate,
                                'symbol': currency_symbols[currency],
                                'updated_at': now,
                                'source': 'ЦБ РФ (принудительное обновление)'
                            }
                        )
                        
                        # Сохраняем историю курса
                        CurrencyRateHistory.objects.create(
                            currency_name=currency,
                            rate=rate,
                            timestamp=now,
                            source='ЦБ РФ (принудительное обновление)'
                        )
                    cls.logger.info("Курсы традиционных валют успешно обновлены из ЦБ РФ (принудительно)")
                except Exception as e:
                    cls.logger.error(f"Ошибка при получении курсов валют через ЦБ РФ: {e}")
                    # Создаем фиксированные значения для отладки
                    cls.logger.warning("Создаем фиксированные значения для валют (принудительно)")
                    for currency, default_rate in {"USD": 90.0, "EUR": 100.0, "CNY": 12.5}.items():
                        try:
                            CurrencyRate.objects.update_or_create(
                                currency_name=currency,
                                defaults={
                                    'rate': default_rate,
                                    'symbol': currency_symbols[currency],
                                    'updated_at': now,
                                    'source': 'Фиксированное значение (принудительное обновление)'
                                }
                            )
                            
                            # Сохраняем историю курса
                            CurrencyRateHistory.objects.create(
                                currency_name=currency,
                                rate=default_rate,
                                timestamp=now,
                                source='Фиксированное значение (принудительное обновление)'
                            )
                        except Exception as inner_e:
                            cls.logger.error(f"Ошибка при создании фиксированного значения для {currency}: {inner_e}")
            else:
                # Обновляем курсы из OpenExchangeRates
                for currency, rate_info in forex_rates.items():
                    if currency in currency_symbols:
                        rate = rate_info['rate']
                        # Обновляем текущий курс
                        CurrencyRate.objects.update_or_create(
                            currency_name=currency,
                            defaults={
                                'rate': rate,
                                'symbol': currency_symbols[currency],
                                'updated_at': now,
                                'source': 'OpenExchangeRates (принудительное обновление)'
                            }
                        )
                        
                        # Сохраняем историю курса
                        CurrencyRateHistory.objects.create(
                            currency_name=currency,
                            rate=rate,
                            timestamp=now,
                            source='OpenExchangeRates (принудительное обновление)'
                        )
                cls.logger.info("Курсы традиционных валют успешно обновлены из OpenExchangeRates (принудительно)")

            # Пробуем получить криптовалютные курсы
            crypto_rates = cls.get_crypto_rates()
            cls.logger.info(f"Результат запроса криптовалютных курсов (force): {crypto_rates}")
            
            # Обновляем криптовалюты
            for crypto, rate in crypto_rates.items():
                # Обновляем текущий курс
                CurrencyRate.objects.update_or_create(
                    currency_name=crypto,
                    defaults={
                        'rate': rate,
                        'symbol': currency_symbols[crypto],
                        'updated_at': now,
                        'source': 'CoinGecko (принудительное обновление)'
                    }
                )
                
                # Сохраняем историю курса
                CurrencyRateHistory.objects.create(
                    currency_name=crypto,
                    rate=rate,
                    timestamp=now,
                    source='CoinGecko (принудительное обновление)'
                )
            cls.logger.info("Курсы криптовалют успешно обновлены (принудительно)")

            cls.logger.info(f"Принудительное обновление курсов валют завершено в: {now}")
            return True
        except Exception as e:
            cls.logger.error(f"Ошибка при принудительном обновлении курсов валют: {e}")
            return False 