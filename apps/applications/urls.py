from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    path('', views.app_list, name='list'),
    path('<str:pk>/', views.app_detail, name='detail'),
]
