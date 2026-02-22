from django.urls import path
from . import views
from apps.mermaid_gen import views as mermaid_views

app_name = 'applications'

urlpatterns = [
    path('', views.app_list, name='list'),
    path('<str:pk>/', views.app_detail, name='detail'),
    path('<str:pk>/mermaid/', mermaid_views.generate_mermaid, name='mermaid'),
]
