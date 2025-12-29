from django.urls import path
from . import web_views

app_name = 'hr_web'

urlpatterns = [
    path('', web_views.hr_dashboard, name='dashboard'),
]
