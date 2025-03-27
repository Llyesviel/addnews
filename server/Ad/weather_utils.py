import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import WeatherCache
import logging

class WeatherService:
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    
    # Координаты Москвы
    DEFAULT_LAT = 55.7558
    DEFAULT_LON = 37.6173
    
    # Словарь соответствия погодных условий и фоновых изображений
    WEATHER_BACKGROUNDS = {
        'Clear': 'ясно.png',
        'Clouds': {
            'few clouds': 'ясно.png',
            'scattered clouds': 'Пасмурно.png',
            'broken clouds': 'Пасмурно.png',
            'overcast clouds': 'Пасмурно.png'
        },
        'Rain': 'дождь.png',
        'Drizzle': 'дождь.png',
        'Thunderstorm': 'Гроза.png',
        'Snow': 'Снег.png',
        'Mist': 'Туман.png',
        'Fog': 'Туман.png',
        'Haze': 'Туман.png'
    }
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENWEATHER_API_KEY', None)
        self.cache_timeout = getattr(settings, 'WEATHER_CACHE_TIMEOUT', 3600)  # 1 час

    def _kelvin_to_celsius(self, kelvin):
        return round(kelvin - 273.15, 1)

    def _get_cached_weather(self, lat, lon, date):
        try:
            cache = WeatherCache.objects.get(
                city=f"{lat},{lon}",
                date=date
            )
            # Проверяем актуальность кэша
            if (timezone.now() - cache.last_updated).seconds < self.cache_timeout:
                return cache
            return None
        except WeatherCache.DoesNotExist:
            return None

    def get_weather_background(self, weather_data):
        """Определяет фоновое изображение на основе погодных данных"""
        if not weather_data or 'weather' not in weather_data:
            return 'Пасмурно.png'  # значение по умолчанию
            
        weather = weather_data['weather'][0]
        main = weather.get('main', '')
        description = weather.get('description', '').lower()
        
        # Проверяем особые случаи для облаков
        if main == 'Clouds' and description in self.WEATHER_BACKGROUNDS['Clouds']:
            return self.WEATHER_BACKGROUNDS['Clouds'][description]
            
        # Для всех остальных случаев
        return self.WEATHER_BACKGROUNDS.get(main, 'Пасмурно.png')

    def _cache_weather(self, weather_data, is_current=True):
        if is_current:
            date = timezone.now().date()
        else:
            date = datetime.fromtimestamp(weather_data['dt']).date()

        # Проверяем наличие необходимых данных
        if 'coord' not in weather_data:
            weather_data['coord'] = {
                'lat': self.DEFAULT_LAT,
                'lon': self.DEFAULT_LON
            }

        try:
            # Добавляем фоновое изображение в кэш
            background_image = self.get_weather_background(weather_data)
            
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
                    'background_image': background_image  # Добавляем новое поле
                }
            )
            return cache
        except KeyError as e:
            logging.error(f"Ошибка при кэшировании погоды: отсутствует ключ {e}")
            return None

    def get_current_weather(self, lat=None, lon=None):
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key is not set")

        lat = lat or self.DEFAULT_LAT
        lon = lon or self.DEFAULT_LON
        
        cached = self._get_cached_weather(lat, lon, timezone.now().date())
        if cached:
            return cached

        url = f"{self.BASE_URL}/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'lang': 'ru',
            'units': 'metric'
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            weather_data = response.json()
            return self._cache_weather(weather_data)
        except requests.RequestException as e:
            raise ValueError(f"Error fetching weather data: {str(e)}")

    def get_forecast(self, lat=None, lon=None, days=6):
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key is not set")

        lat = lat or self.DEFAULT_LAT
        lon = lon or self.DEFAULT_LON

        url = f"{self.BASE_URL}/forecast"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'lang': 'ru',
            'units': 'metric'
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            forecast_data = response.json()

            # Группируем прогноз по дням
            daily_forecast = {}
            for item in forecast_data['list']:
                date = datetime.fromtimestamp(item['dt']).date()
                if date > timezone.now().date() and len(daily_forecast) < days:
                    if date not in daily_forecast:
                        daily_forecast[date] = item
                        self._cache_weather(item, is_current=False)

            return [self._cache_weather(data, is_current=False) 
                   for data in daily_forecast.values()]
        except requests.RequestException as e:
            raise ValueError(f"Error fetching forecast data: {str(e)}")

weather_service = WeatherService() 