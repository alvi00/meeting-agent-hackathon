# management/commands/run_google_meet_bot.py
from django.core.management.base import BaseCommand
from create_meeting_app.bot_scripts.google_meet_bot import join_meeting

class Command(BaseCommand):
    help = "Launch a Selenium bot to join Google Meet"

    def add_arguments(self, parser):
        parser.add_argument('--url', required=True, type=str, help="Google Meet URL")
        parser.add_argument('--name', required=True, type=str, help="Bot display name")

    def handle(self, *args, **opts):
        join_meeting(opts['url'], opts['name'])