from django.urls import path
from . import views

app_name = 'ai_analysis'

urlpatterns = [
    path('', views.analysis_page, name='analysis'),
    path('stream/', views.analysis_stream, name='stream'),
]
