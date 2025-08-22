from django.urls import path
from .views import dashboard, create_meeting, join_meeting, meeting_page, delete_meeting, transcribe_meeting_view, summarize_transcript,ask_meeting_question
from create_meeting_app.views import download_summary_pdf

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('create/', create_meeting, name='create_meeting'),
    path('join/', join_meeting, name='join_meeting'),
    path('meeting/<int:meeting_id>/', meeting_page, name='meeting_page'),
    path('delete_meeting/<int:meeting_id>/', delete_meeting, name='delete_meeting'),
    path('meeting/<int:meeting_id>/transcribe/', transcribe_meeting_view, name='transcribe_meeting'),
    path('dashboard/transcript/<int:transcript_id>/summarize/', summarize_transcript, name='summarize_transcript'),
    path('meeting/<int:meeting_id>/download_pdf/', download_summary_pdf, name='download_summary_pdf'),
    path('meeting/<int:meeting_id>/ask/', ask_meeting_question, name='ask_meeting_question'),

]