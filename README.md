# AdNews

## Локальная установка
**Версия питона 3.12**

### Создать окружение
```bash
python3 -m venv venv
```
### Установить бибы
```bash
pip install -r server/requirements.txt
```
### Запуск сервера
```bash
python server/manage.py runserver
```
**В settings.py использовать .env.debug**
```bash
python server/manage.py createsuperuser
```
### Настройка IDE

Settings - Project - Project Structure

Папку server назначить source. 
Папки docker, venv, static - excluded.

## Управление контейнерами

**Создать локальный файл .env, используя .env.template**

**В settings.py использовать .env**

### Билд (с запуском)
```bash
docker-compose -p adnews up --build -d
```

### Запуск
```bash
docker-compose -p adnews up -d
```
Для запуска не в фоне убрать "-d"

### Рестарт
```bash
docker-compose -p adnews restart
```

### Выкл
```bash
docker-compose -p adnews down
```

## Добавить инструкции по установке зависимостей OpenCV

### Установка зависимостей OpenCV

При использовании `opencv-python` убедитесь, что все системные зависимости установлены. Для Docker это уже настроено через `Dockerfile`. Для локальной разработки установите необходимые библиотеки:

#### Для Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y libglib2.0-0 libsm6 libxext6 libxrender-dev
```

#### Для MacOS:
```bash
brew install opencv
```

#### Для Windows:
Убедитесь, что установлены все необходимые DLL-файлы и библиотеки. Рекомендуется использовать готовые бинарные сборки через pip:
```bash
pip install opencv-python
```

После установки системных зависимостей, установите Python-зависимости:
```bash
pip install -r server/requirements.txt
```


```bash
docker build -t batbka/adnews-server:v1.9 -f docker/django/Dockerfile-prod.txt .
```
```bash
docker run --env-file .env.debug --name adnews-prod -p 8000:8000 batbka/adnews-server:v1.9
```
```bash
docker login
```
```bash
docker push batbka/adnews-server:v1.9
```