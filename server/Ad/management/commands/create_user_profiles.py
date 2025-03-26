from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Ad.models import UserProfile

class Command(BaseCommand):
    help = 'Создает профили для всех пользователей, у которых их нет'

    def handle(self, *args, **options):
        users_without_profile = User.objects.filter(userprofile__isnull=True)
        created_count = 0
        
        for user in users_without_profile:
            UserProfile.objects.create(user=user)
            created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно создано {created_count} профилей пользователей'
            )
        ) 