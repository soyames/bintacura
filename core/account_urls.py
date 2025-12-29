from django.urls import path
from . import account_views

app_name = 'account'

urlpatterns = [
    path('sessions/', account_views.sessions_view, name='sessions'),
    path('export-data/', account_views.export_data_view, name='export_data'),
    path('emergency-contacts/', account_views.emergency_contacts_view, name='emergency_contacts'),
    path('deactivate/', account_views.deactivate_account_view, name='deactivate'),
    path('delete-permanently/', account_views.delete_account_permanently_view, name='delete_permanently'),  # ISSUE-PAT-056
]
