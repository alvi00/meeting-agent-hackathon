from django.core.management.base import BaseCommand
from create_meeting_app.models import Meeting
from datetime import datetime, timedelta
from create_meeting_app.bot_scripts.google_meet_bot import join_meeting

class Command(BaseCommand):
    help = "Checks for meetings to join and uses bot to join"

    def handle(self, *args, **kwargs):
        now = datetime.now().time().replace(second=0, microsecond=0)
        five_minutes_ago = (datetime.now() - timedelta(minutes=5)).time().replace(second=0, microsecond=0)
        one_minute_later = (datetime.now() + timedelta(minutes=1)).time().replace(second=0, microsecond=0)

        print(f"⌚ Checking meetings between {five_minutes_ago} and {one_minute_later}")
        meetings_to_join = Meeting.objects.filter(
            join_time__gte=five_minutes_ago,
            join_time__lt=one_minute_later,
            joined=False
        )

        if not meetings_to_join.exists():
            self.stdout.write("📭 No meetings to join at this time.")
            return

        for meeting in meetings_to_join:
            self.stdout.write(f"🤖 Joining meeting: {meeting.name} as bot '{meeting.bot_name}'")
            try:
                # Pass the Meeting instance to the function
                join_meeting(meeting.meeting_link, meeting.bot_name, meeting)
                meeting.joined = True
                meeting.save()
                self.stdout.write("✅ Marked as joined.")
            except Exception as e:
                self.stdout.write(f"❌ Failed to join: {e}")