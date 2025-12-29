from django.urls import path
from .views import GenerateQRCodeView, GetQRCodeView

app_name = 'qrcode_generator'

urlpatterns = [
    path('generate/', GenerateQRCodeView.as_view(), name='generate-qr-code'),
    path('get/<str:content_type>/<uuid:object_id>/', GetQRCodeView.as_view(), name='get-qr-code'),
]
