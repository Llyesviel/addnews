# Запуск тестов для проекта

Этот документ описывает, как запускать юнит-тесты для проекта.

## Структура тестов

Тесты организованы в следующие файлы:

- `test_models.py`: тесты для моделей данных
- `test_views.py`: тесты для представлений и шаблонов
- `test_api.py`: тесты для API-эндпоинтов

## Как запускать тесты

### Запуск всех тестов

```bash
python manage.py test Ad
```

### Запуск тестов из конкретного файла

```bash
python manage.py test Ad.tests.test_models
python manage.py test Ad.tests.test_views
python manage.py test Ad.tests.test_api
```

### Запуск конкретного тестового класса

```bash
python manage.py test Ad.tests.test_models.NewsModelTest
```

### Запуск конкретного теста

```bash
python manage.py test Ad.tests.test_models.NewsModelTest.test_news_creation
```

### Запуск с расширенным выводом

```bash
python manage.py test Ad --verbosity=2
```

## Проверка покрытия кода тестами

Для проверки покрытия кода тестами установите пакет `coverage`:

```bash
pip install coverage
```

### Запуск тестов с проверкой покрытия

```bash
coverage run --source='Ad' manage.py test Ad
```

### Просмотр отчета в консоли

```bash
coverage report
```

### Создание HTML-отчета

```bash
coverage html
```

После выполнения этой команды отчет будет доступен в директории `htmlcov`. 