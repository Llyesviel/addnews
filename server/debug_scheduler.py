import os
import sys
import json
from datetime import datetime
import inspect

# Добавляем путь к Django проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from Ad.tasks import SchedulerSingleton

def get_scheduler_status():
    """Получение статуса планировщика и его задач"""
    # Получаем доступ к планировщику напрямую без инициализации
    scheduler_instance = getattr(SchedulerSingleton, '_scheduler', None)
    
    if scheduler_instance is None:
        return {
            "status": "Планировщик не инициализирован",
            "timestamp": datetime.now().isoformat()
        }
    
    jobs = []
    for job in scheduler_instance.get_jobs():
        job_info = {
            "id": job.id,
            "name": job.func.__name__ if hasattr(job.func, '__name__') else str(job.func),
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
            "misfire_grace_time": job.misfire_grace_time
        }
        jobs.append(job_info)
    
    # Проверяем исходный код метода update_currency_job
    source_code = inspect.getsource(SchedulerSingleton.update_currency_job)
    
    # Проверяем наличие ограничения по времени (если строка не закомментирована)
    time_check_line = "if now.minute != 0:"
    time_check_commented = time_check_line in source_code and "#" + time_check_line in source_code
    
    result = {
        "status": "Активен" if scheduler_instance.running else "Остановлен",
        "jobs": jobs,
        "job_count": len(jobs),
        "has_time_restriction_commented": time_check_commented,
        "source_code_fragment": source_code[:500],  # Часть исходного кода для проверки
        "timestamp": datetime.now().isoformat()
    }
    
    return result

if __name__ == "__main__":
    # Прямой доступ к переменным класса, чтобы не вызывать инициализацию планировщика
    print("Проверка кода планировщика и задач валют")
    
    # Получаем исходный код метода update_currency_job
    source_code = inspect.getsource(SchedulerSingleton.update_currency_job)
    
    # Проверяем строки кода, которые могут повлиять на обновление
    time_check_code = "if now.minute != 0:"
    comment_marker = "#"
    
    print(f"Ограничение по времени закомментировано: {comment_marker + time_check_code in source_code}")
    
    # Создадим файл с исходным кодом метода
    with open("update_currency_job.txt", "w", encoding="utf-8") as f:
        f.write(source_code)
    
    print("Исходный код метода update_currency_job сохранен в файл update_currency_job.txt")
    
    # Сохраняем другую информацию о планировщике
    try:
        status = get_scheduler_status()
        with open("scheduler_status.json", "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
        print("Информация о планировщике сохранена в файл scheduler_status.json")
    except Exception as e:
        print(f"Ошибка при получении статуса планировщика: {e}") 