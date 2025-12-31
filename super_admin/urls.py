from django.urls import path
from . import views

app_name = 'super_admin'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('verification/queue/', views.verification_queue, name='verification_queue'),
    path('verification/<uuid:uid>/', views.verification_detail, name='verification_detail'),
    path('participants/', views.participants_list, name='participants_list'),
    path('financial/', views.financial_reports, name='financial_reports'),
]
