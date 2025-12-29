from django.urls import path
from . import web_views

app_name = 'financial_web'

urlpatterns = [
    path('', web_views.financial_dashboard, name='dashboard'),
]
