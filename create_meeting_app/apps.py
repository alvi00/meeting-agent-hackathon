from django.apps import AppConfig

class CreateMeetingAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'create_meeting_app'

    def ready(self):
        # DO NOT start the scheduler here. Let the DB finish migrating first.
        pass
