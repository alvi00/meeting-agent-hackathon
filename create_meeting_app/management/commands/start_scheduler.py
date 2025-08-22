from django.core.management.base import BaseCommand
from create_meeting_app.scheduler import start

class Command(BaseCommand):
    help = 'Starts the background APScheduler'

    def handle(self, *args, **options):
        start()
        self.stdout.write(self.style.SUCCESS("🎯 APScheduler started successfully!"))
