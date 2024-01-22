from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Create default superuser'

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'rsstranslator')
            self.stdout.write(self.style.SUCCESS('Successfully created a new superuser: admin, Password: rsstranslator'))

        else:
            self.stdout.write(self.style.SUCCESS('Superuser already exists'))