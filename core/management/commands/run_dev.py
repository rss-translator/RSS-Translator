import os
import subprocess
import sys
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Please make sure you have installed the required packages for dev."
    def handle(self, *args, **options):
        # Set DEBUG environment variable to '1'
        os.environ['DEBUG'] = '1'

        # Run collectstatic, makemigrations, and migrate
        call_command('collectstatic', '--no-input')
        call_command('makemigrations')
        call_command('migrate')

        # Start run_huey in a separate process
        subprocess.Popen([sys.executable, 'manage.py', 'run_huey'])

        # Create default superuser
        call_command('create_default_superuser')

        # Run the server
        call_command('runserver')
