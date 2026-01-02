from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'cycles', views.MenstrualCycleViewSet, basename='cycle')
router.register(r'symptoms', views.CycleSymptomViewSet, basename='symptom')
router.register(r'reminders', views.CycleReminderViewSet, basename='reminder')

urlpatterns = [
    path('', include(router.urls)),
]
