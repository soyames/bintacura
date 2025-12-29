from django.urls import path
from .views import (
    survey_stats_view,
    survey_submit_view,
    survey_thank_you_view,
    export_survey_data_view
)

urlpatterns = [
    path('', survey_stats_view, name='survey_stats'),
    path('submit/', survey_submit_view, name='survey_submit'),
    path('thank-you/', survey_thank_you_view, name='survey_thank_you'),
    path('export/csv/', export_survey_data_view, {'file_format': 'csv'}, name='survey_export_csv'),
    path('export/excel/', export_survey_data_view, {'file_format': 'excel'}, name='survey_export_excel'),
    path('export/pdf/', export_survey_data_view, {'file_format': 'pdf'}, name='survey_export_pdf'),
]
