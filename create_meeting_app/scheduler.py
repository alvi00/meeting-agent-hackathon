# create_meeting_app/scheduler.py

from apscheduler.schedulers.blocking import BlockingScheduler
from django_apscheduler.jobstores import DjangoJobStore
from create_meeting_app.bot_scripts import google_meet_bot
from create_meeting_app.models import Meeting
from datetime import datetime, timedelta

def check_and_run_meetings():
    now = datetime.now().time().replace(second=0, microsecond=0)
    five_minutes_ago = (datetime.now() - timedelta(minutes=5)).time().replace(second=0, microsecond=0)
    one_minute_later = (datetime.now() + timedelta(minutes=1)).time().replace(second=0, microsecond=0)

    meetings = Meeting.objects.filter(
        join_time__gte=five_minutes_ago,
        join_time__lt=one_minute_later,
        joined=False
    )
    for meeting in meetings:
        print(f"🤖 Joining meeting: {meeting.name}")

        # Mark as joined immediately to prevent duplicate browsers
        meeting.joined = True
        meeting.save()

        try:
            google_meet_bot.join_meeting(meeting.meeting_link, meeting.bot_name, meeting)
            print("✅ Successfully joined.")
        except Exception as e:
            print(f"❌ Failed to join meeting: {e}")
            # If you want to retry on failure, undo the flag here:
            # meeting.joined = False
            # meeting.save()

def start():
    # Use in-memory jobstore to prevent SQLite locking issues
    scheduler = BlockingScheduler(jobstores={})

    scheduler.add_job(
        check_and_run_meetings,
        trigger='interval',
        minutes=1,
        name='check_and_run_meetings_job',
        replace_existing=True,
        max_instances=3,
        coalesce=True,
    )

    print("🔁 BlockingScheduler starting...")
    scheduler.start()
    print("🛑 BlockingScheduler stopped.")

