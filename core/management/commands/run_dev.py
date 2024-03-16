import os
import subprocess
import sys
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    '''
    1. pip install -r requirements/dev
    2. enable gevent compatible for your IDE
        ex: PyCharm-> Preferences -> Build, Execution, Deployment -> Python Debugger -> check Gevent compatible
    3. set the debug custom command to run_dev
    '''
    help = 'Initialize the server for DEV.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.process = None

    def handle(self, *args, **options):
        # Set DEBUG environment variable to '1'
        os.environ['DEBUG'] = '1'

        # Run collectstatic, makemigrations, and migrate
        call_command('collectstatic', '--no-input')
        call_command('makemigrations')
        call_command('migrate')

        # Start run_huey in a separate process using the same Python interpreter
        self.process = subprocess.Popen([sys.executable, 'manage.py', 'run_huey'])

        # Create default superuser
        call_command('create_default_superuser')

        # Run the server
        try:
            call_command('runserver')
        finally:
            # Attempt to terminate the subprocess when the server is stopped
            if self.process:
                self.process.terminate()
                self.process.wait()

