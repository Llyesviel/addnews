import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import WeatherCache
import logging
import os
import subprocess

class WeatherService:
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    
    # Словарь городов с координатами и часовыми поясами
    CITIES = {
        'Москва': {
            'lat': 55.7522,
            'lon': 37.6156,
            'timezone_offset': 3  # UTC+3
        },
        'Санкт-Петербург': {
            'lat': 59.9386,
            'lon': 30.3141,
            'timezone_offset': 3  # UTC+3
        },
        'Пермь': {
            'lat': 58.0105,
            'lon': 56.2502,
            'timezone_offset': 5  # UTC+5
        },
        'Хабаровск': {
            'lat': 48.4827,
            'lon': 135.084,
            'timezone_offset': 10  # UTC+10
        }
    }
    
    # Текущий город по умолчанию
    DEFAULT_CITY = 'Москва'
    
    # Координаты Москвы по умолчанию
    DEFAULT_LAT = 55.7522
    DEFAULT_LON = 37.6156
    
    # Словарь соответствия погодных условий и фоновых изображений
    WEATHER_BACKGROUNDS = {
        'Clear': 'clear.png',
        'Clouds': {
            'few clouds': 'clear.png',
            'scattered clouds': 'cloudy.png',
            'broken clouds': 'cloudy.png',
            'overcast clouds': 'cloudy.png'
        },
        'Rain': 'rain.png',
        'Drizzle': 'rain.png',
        'Thunderstorm': 'thunderstorm.png',
        'Snow': 'snow.png',
        'Mist': 'fog.png',
        'Fog': 'fog.png',
        'Haze': 'fog.png'
    }
    
    def __init__(self):
        # Загрузка API ключа из настроек или файла
        api_key = os.environ.get('OPENWEATHER_API_KEY')
        
        # Если ключа нет в переменных окружения, пытаемся загрузить из настроек
        self.api_key = api_key or getattr(settings, 'OPENWEATHER_API_KEY', None)
        
        # Настройка времени кэширования
        self.cache_timeout = getattr(settings, 'WEATHER_CACHE_TIMEOUT', 1800)  # 30 минут
        
        # Установка текущего города по умолчанию
        self.current_city = self.DEFAULT_CITY

    def get_current_city(self):
        """Возвращает текущий выбранный город"""
        return self.current_city
        
    def get_city_list(self):
        """Возвращает список доступных городов"""
        return list(self.CITIES.keys())
        
    def set_city(self, city_name):
        """Устанавливает текущий город по имени"""
        if city_name in self.CITIES:
            self.current_city = city_name
            return True
        return False
        
    def next_city(self):
        """Переключает на следующий город в списке"""
        city_list = self.get_city_list()
        current_index = city_list.index(self.current_city)
        next_index = (current_index + 1) % len(city_list)
        self.current_city = city_list[next_index]
        return self.current_city
        
    def prev_city(self):
        """Переключает на предыдущий город в списке"""
        city_list = self.get_city_list()
        current_index = city_list.index(self.current_city)
        prev_index = (current_index - 1) % len(city_list)
        self.current_city = city_list[prev_index]
        return self.current_city
        
    def get_city_coords(self, city_name=None):
        """Возвращает координаты указанного города или текущего города"""
        city = city_name or self.current_city
        if city in self.CITIES:
            return self.CITIES[city]['lat'], self.CITIES[city]['lon']
        return self.DEFAULT_LAT, self.DEFAULT_LON
        
    def get_city_timezone_offset(self, city_name=None):
        """Возвращает смещение часового пояса для города"""
        city = city_name or self.current_city
        
        if city in self.CITIES:
            tz_offset = self.CITIES[city]['timezone_offset']
            logging.debug(f"Часовой пояс для города {city}: UTC+{tz_offset}")
            return tz_offset
        
        # Значение по умолчанию - московское время (UTC+3)
        logging.warning(f"Используем часовой пояс по умолчанию (UTC+3) для города {city}")
        return 3

    def _test_api_key(self):
        """Проверяет работоспособность API ключа"""
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key is not set")
            
        lat, lon = self.get_city_coords()
        url = f"{self.BASE_URL}/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False

    def _get_cached_weather(self, lat, lon, date):
        try:
            cache = WeatherCache.objects.get(
                city=f"{lat},{lon}",
                date=date
            )
            # Проверяем актуальность кэша
            if (timezone.now() - cache.last_updated).seconds < self.cache_timeout:
                logging.info(f"Использую кэш погоды для {lat},{lon} на {date}")
                return cache
            logging.info(f"Кэш для {lat},{lon} на {date} устарел")
            return None
        except WeatherCache.DoesNotExist:
            logging.info(f"Кэш для {lat},{lon} на {date} не найден")
            return None

    def get_weather_background(self, weather_data):
        """Определяет фоновое изображение на основе погодных данных"""
        if not weather_data or 'weather' not in weather_data:
            return 'cloudy.png'  # значение по умолчанию
            
        weather = weather_data['weather'][0]
        main = weather.get('main', '')
        description = weather.get('description', '').lower()
        
        # Проверяем особые случаи для облаков
        if main == 'Clouds' and description in self.WEATHER_BACKGROUNDS['Clouds']:
             return self.WEATHER_BACKGROUNDS['Clouds'][description]
            
        # Для всех остальных случаев
        return self.WEATHER_BACKGROUNDS.get(main, 'cloudy.png')

    def _cache_weather(self, weather_data, is_current=True):
        # Определяем город по координатам
        city_name = self.current_city
        
        if is_current:
            # Используем часовой пояс выбранного города
            tz_offset = self.get_city_timezone_offset()
            city_tz = timedelta(hours=tz_offset)
            now_city = datetime.now() + city_tz
            date = now_city.date()
        else:
            # Для прогноза используем часовой пояс выбранного города
            tz_offset = self.get_city_timezone_offset()
            city_tz = timedelta(hours=tz_offset)
            utc_time = datetime.fromtimestamp(weather_data['dt'])
            city_time = utc_time + city_tz
            date = city_time.date()

        # Проверяем наличие необходимых данных
        if 'coord' not in weather_data:
            weather_data['coord'] = {
                'lat': self.DEFAULT_LAT,
                'lon': self.DEFAULT_LON
            }
            
        # Определяем фоновое изображение
        background_image = self.get_weather_background(weather_data)

        try:
            cache, created = WeatherCache.objects.update_or_create(
                city=f"{weather_data['coord']['lat']},{weather_data['coord']['lon']}",
                date=date,
                defaults={
                    'temperature': float(weather_data['main']['temp']),
                    'feels_like': float(weather_data['main']['feels_like']),
                    'humidity': weather_data['main']['humidity'],
                    'pressure': weather_data['main']['pressure'],
                    'wind_speed': weather_data['wind']['speed'],
                    'description': weather_data['weather'][0]['description'],
                    'icon': weather_data['weather'][0]['icon'],
                    'background_image': background_image
                }
            )
            return cache
        except KeyError as e:
            logging.error(f"Ошибка при кэшировании погоды: {e}")
            return None

    def get_current_weather(self, lat=None, lon=None, city_name=None):
        """Получает текущую погоду"""
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key is not set")

        # Если город указан, используем его координаты
        if city_name:
            lat, lon = self.get_city_coords(city_name)
        # Если координаты не указаны явно, используем координаты текущего города
        elif lat is None or lon is None:
            lat, lon = self.get_city_coords()
        
        # Проверяем кэш
        cached = self._get_cached_weather(lat, lon, timezone.now().date())
        if cached:
            return cached

        # Запрос к API
        url = f"{self.BASE_URL}/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'lang': 'ru',
            'units': 'metric'
        }

        try:
            logging.info(f"Запрос текущей погоды: {url}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            weather_data = response.json()
            logging.debug(f"Получены данные о погоде: {weather_data}")
            
            return self._cache_weather(weather_data)
        except requests.RequestException as e:
            logging.error(f"Ошибка запроса погоды: {e}")
            raise ValueError(f"Ошибка при получении данных о погоде: {str(e)}")
            
    def get_hourly_forecast(self, lat=None, lon=None, hours=8, city_name=None):
        """Получить почасовой прогноз погоды"""
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key is not set")

        # Если город указан, используем его координаты
        if city_name:
            lat, lon = self.get_city_coords(city_name)
        # Если координаты не указаны явно, используем координаты текущего города
        elif lat is None or lon is None:
            lat, lon = self.get_city_coords()

        url = f"{self.BASE_URL}/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'lang': 'ru',
            'units': 'metric'
        }

        try:
            logging.info(f"Запрос почасового прогноза")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            forecast_data = response.json()
            hourly_forecast = []
            
            # Используем часовой пояс выбранного города
            tz_offset = self.get_city_timezone_offset(city_name)
            city_tz = timedelta(hours=tz_offset)
            
            # Обрабатываем только необходимое количество часов
            for i, item in enumerate(forecast_data.get('list', [])):
                if i >= hours:
                    break
                    
                # Получаем время по UTC и добавляем смещение для получения времени города
                utc_time = datetime.fromtimestamp(item['dt'])
                city_time = utc_time + city_tz
                
                hourly_forecast.append({
                    'time': city_time.strftime('%H:%M'),
                    'icon': item['weather'][0]['icon'],
                    'temp': item['main']['temp'],
                    'description': item['weather'][0]['description']
                })
                
            return hourly_forecast
        except requests.RequestException as e:
            logging.error(f"Ошибка запроса почасового прогноза: {e}")
            raise ValueError(f"Ошибка при получении почасового прогноза: {str(e)}")

    def get_forecast(self, lat=None, lon=None, days=6, city_name=None):
        """Получает прогноз погоды на несколько дней"""
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key is not set")

        # Если город указан, используем его координаты
        if city_name:
            lat, lon = self.get_city_coords(city_name)
        # Если координаты не указаны явно, используем координаты текущего города
        elif lat is None or lon is None:
            lat, lon = self.get_city_coords()

        url = f"{self.BASE_URL}/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'lang': 'ru',
            'units': 'metric'
        }

        try:
            logging.info(f"Запрос прогноза погоды на {days} дней")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            forecast_data = response.json()
            logging.debug(f"Получено {len(forecast_data.get('list', []))} точек данных")

            # Используем часовой пояс выбранного города
            tz_offset = self.get_city_timezone_offset(city_name)
            city_tz = timedelta(hours=tz_offset)
            
            # Текущая дата по времени выбранного города
            now_city = datetime.now() + city_tz
            today_city = now_city.date()

            # Группируем прогноз по дням, предпочитая дневные часы
            daily_forecast = {}
            
            for item in forecast_data.get('list', []):
                # Получаем время по UTC и добавляем смещение для получения времени города
                utc_time = datetime.fromtimestamp(item['dt'])
                city_time = utc_time + city_tz
                date = city_time.date()
                hour = city_time.hour
                
                # Пропускаем текущий день по времени выбранного города, начинаем со следующего
                if date <= today_city:
                    continue
                    
                # Если уже набрали нужное количество дней, выходим
                if len(daily_forecast) >= days:
                    break
                
                # Предпочитаем точки данных в середине дня (12-15 часов) для лучшего прогноза
                if date not in daily_forecast:
                    # Первый прогноз для этого дня
                    daily_forecast[date] = item
                elif 12 <= hour <= 15:
                    # Обновляем на дневной прогноз если доступен
                    daily_forecast[date] = item

            return [self._cache_weather(data, is_current=False) 
                   for data in daily_forecast.values()]
        except requests.RequestException as e:
            logging.error(f"Ошибка запроса прогноза: {e}")
            raise ValueError(f"Ошибка при получении прогноза погоды: {str(e)}")

# Создаем экземпляр сервиса погоды
weather_service = WeatherService() 