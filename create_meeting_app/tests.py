from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from .models import Meeting
from django.utils import timezone
from datetime import datetime, timedelta

class MeetingViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create a test meeting
        self.meeting = Meeting.objects.create(
            user=self.user,
            name="Test Meeting",
            bot_name="TestBot",
            meeting_link="https://meet.google.com/test",
            join_time=timezone.now().time(),
            is_active=True
        )

    def test_dashboard_view(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertIn('meetings', response.context)
        self.assertEqual(list(response.context['meetings']), [self.meeting])

    def test_create_meeting_view_success(self):
        meeting_data = {
            'name': 'New Test Meeting',
            'bot_name': 'NewTestBot',
        }
        response = self.client.post(reverse('create_meeting'), meeting_data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Meeting.objects.filter(name='New Test Meeting').exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Meeting created successfully!')

    def test_create_meeting_view_invalid_data(self):
        meeting_data = {
            'name': '',  # Invalid: empty name
            'bot_name': 'NewTestBot',
        }
        response = self.client.post(reverse('create_meeting'), meeting_data)
        self.assertEqual(response.status_code, 302)  # Redirects even on failure
        self.assertFalse(Meeting.objects.filter(bot_name='NewTestBot').exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Error creating meeting. Please check the form.')

    def test_join_meeting_view_success(self):
        join_data = {
            'meeting_id': self.meeting.id,
            'meeting_link': 'https://meet.google.com/updated-test',
            'join_time': timezone.now().time()
        }
        response = self.client.post(reverse('join_meeting'), join_data)
        self.assertEqual(response.status_code, 302)
        updated_meeting = Meeting.objects.get(pk=self.meeting.id)
        self.assertEqual(updated_meeting.meeting_link, 'https://meet.google.com/updated-test')
        self.assertFalse(updated_meeting.joined)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Meeting details saved! Bot will join on time.')

    def test_join_meeting_view_invalid_data(self):
        join_data = {
            'meeting_id': self.meeting.id,
            'meeting_link': '',  # Invalid: empty link
            'join_time': timezone.now().time()
        }
        response = self.client.post(reverse('join_meeting'), join_data)
        self.assertEqual(response.status_code, 302)
        updated_meeting = Meeting.objects.get(pk=self.meeting.id)
        self.assertEqual(updated_meeting.meeting_link, 'https://meet.google.com/test')  # Link should not change
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Error saving meeting details.')

    def test_meeting_page_view(self):
        response = self.client.get(reverse('meeting_page', kwargs={'meeting_id': self.meeting.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'meeting_page.html')
        self.assertEqual(response.context['meeting'], self.meeting)

    def test_delete_meeting_view(self):
        response = self.client.post(reverse('delete_meeting', kwargs={'meeting_id': self.meeting.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertFalse(Meeting.objects.filter(pk=self.meeting.id).exists())

    def test_unauthorized_access(self):
        # Create another user
        other_user = self.User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Create a meeting for the other user
        other_meeting = Meeting.objects.create(
            user=other_user,
            name="Other's Meeting",
            bot_name="OtherBot",
            is_active=True
        )
        
        # Try to access other user's meeting
        response = self.client.get(reverse('meeting_page', kwargs={'meeting_id': other_meeting.id}))
        self.assertEqual(response.status_code, 404)
        
        # Try to delete other user's meeting
        response = self.client.post(reverse('delete_meeting', kwargs={'meeting_id': other_meeting.id}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Meeting.objects.filter(pk=other_meeting.id).exists())