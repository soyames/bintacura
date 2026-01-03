from django.urls import path
from . import views

app_name = 'menstruation'

urlpatterns = [
    # Web views
    path('', views.menstruation_tracker, name='tracker'),
    path('log-period/', views.log_period, name='log_period'),
    path('cycle/<uuid:cycle_id>/', views.cycle_details, name='cycle_details'),
    path('cycle/<uuid:cycle_id>/log-symptom/', views.log_symptom, name='log_symptom'),
    path('calendar/', views.cycle_calendar, name='calendar'),
]
