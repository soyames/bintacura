from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import QRCodeService

class GenerateQRCodeView(APIView):
    def post(self, request):
        content_type = request.data.get('content_type')
        object_id = request.data.get('object_id')
        data_dict = request.data.get('data', {})
        
        if not content_type or not object_id:
            return Response({'error': 'content_type and object_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        qr_code = QRCodeService.generate_qr_code(content_type, object_id, data_dict)
        
        return Response({
            'qr_code_id': str(qr_code.id),
            'qr_code_url': request.build_absolute_uri(qr_code.qr_code_image.url) if qr_code.qr_code_image else None
        }, status=status.HTTP_201_CREATED)

class GetQRCodeView(APIView):
    def get(self, request, content_type, object_id):
        qr_code = QRCodeService.get_qr_code(content_type, object_id)
        
        if not qr_code:
            return Response({'error': 'QR Code not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'qr_code_id': str(qr_code.id),
            'qr_code_url': request.build_absolute_uri(qr_code.qr_code_image.url) if qr_code.qr_code_image else None,
            'qr_code_data': qr_code.qr_code_data
        })
