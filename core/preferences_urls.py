from django.urls import path
from .preferences_views import (
    ParticipantPreferencesView,
    EmergencyContactListView,
    EmergencyContactDetailView,
    LanguagePreferenceView,
)

app_name = 'preferences'

urlpatterns = [
    path('', ParticipantPreferencesView.as_view(), name='preferences'),
    path('language/', LanguagePreferenceView.as_view(), name='language-preference'),
    path('emergency-contacts/', EmergencyContactListView.as_view(), name='emergency-contacts-list'),
    path('emergency-contacts/<uuid:pk>/', EmergencyContactDetailView.as_view(), name='emergency-contact-detail'),
]
