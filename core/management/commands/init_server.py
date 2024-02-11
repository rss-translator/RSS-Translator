from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Initialize the server by running collectstatic, makemigrations, migrate and create_default_superuser commands.'

    def handle(self, *args, **options):
        call_command('collectstatic', '--no-input')
        call_command('makemigrations')
        call_command('migrate')
        call_command('create_default_superuser')
