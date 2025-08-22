from django import forms
from .models import Meeting

class CreateMeetingForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ['name', 'bot_name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Meeting Name'}),
            'bot_name': forms.TextInput(attrs={'placeholder': 'Bot Name'}),
        }

class JoinMeetingForm(forms.Form):
    meeting_id = forms.IntegerField(widget=forms.HiddenInput())
    meeting_link = forms.URLField(widget=forms.URLInput(attrs={'placeholder': 'Meeting Link'}))
    join_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))