from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .review_views import ReviewViewSet, leave_review_view, reviews_list_view, my_reviews_view

app_name = 'appointments'

router = DefaultRouter()
router.register(r'appointments', views.AppointmentViewSet, basename='appointment')
router.register(r'availability', views.AvailabilityViewSet, basename='availability')
router.register(r'queue', views.AppointmentQueueViewSet, basename='queue')
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('', include(router.urls)),
    path('leave-review/<uuid:appointment_id>/', leave_review_view, name='leave-review'),
    path('reviews/list/', reviews_list_view, name='reviews-list'),
    path('my-reviews/', my_reviews_view, name='my-reviews'),
]
