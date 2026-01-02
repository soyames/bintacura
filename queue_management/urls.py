"""
Queue Management URLs
Handles appointment queues, patient calling, and queue status
"""
from django.urls import path
from queue_management import views

app_name = 'queue_management'

urlpatterns = [
    # Patient booking with queue
    path('api/v1/queue/book-appointment/', views.BookAppointmentWithQueueView.as_view(), name='book_appointment_with_queue'),
    
    # Queue status
    path('api/v1/queue/status/', views.get_queue_status, name='queue_status'),
    path('api/v1/queue/status/<uuid:participant_id>/', views.get_provider_queue_status, name='provider_queue_status'),
    
    # Patient queue position
    path('api/v1/queue/my-position/<str:appointment_id>/', views.get_my_queue_position, name='my_queue_position'),
    
    # Provider actions
    path('api/v1/queue/call-next/', views.call_next_patient, name='call_next_patient'),
    path('api/v1/queue/complete/<str:appointment_id>/', views.complete_appointment_with_queue, name='complete_appointment'),
    

]
