from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('start/', views.start_interview, name='start_interview'),
    path('preparing/<int:session_id>/', views.preparing, name='preparing'),
    path('session/<int:session_id>/', views.interview_session, name='interview_session'),
    path('api/ask/', views.ask_question_api, name='ask_question_api'),
    path('api/answer/', views.answer_api, name='answer_api'),
    path('api/stt/', views.deepgram_stt_api, name='deepgram_stt_api'),
    path('api/tts/', views.deepgram_tts_api, name='deepgram_tts_api'),
    path('api/export_csv/', views.export_csv_api, name='export_csv_api'),
    path('api/upload_recording/', views.upload_recording_api, name='upload_recording_api'),
    
    path('session_summary/', views.session_summary_api, name='session_summary_api'),
    path('session_analytics/', views.session_analytics_api, name='session_analytics_api'),
    path('evaluation_report/', views.evaluation_report_api, name='evaluation_report_api'),
    # Add more endpoints as needed for live transcription, video, etc.
] 