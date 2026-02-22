from django.urls import path
from . import views

app_name = 'ai_chat'

urlpatterns = [
    path('', views.chat_page, name='chat'),
    path('stream/', views.chat_stream, name='stream'),
]
