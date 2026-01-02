from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from .services import QRCodeService


class QRCodeRequestSerializer(serializers.Serializer):
    content_type = serializers.CharField()
    object_id = serializers.UUIDField()
    data = serializers.JSONField(required=False, default=dict)


class QRCodeResponseSerializer(serializers.Serializer):
    qr_code_id = serializers.UUIDField()
    qr_code_url = serializers.URLField(allow_null=True)
    qr_code_data = serializers.JSONField(required=False)


@extend_schema(tags=["QR Code"])
class GenerateQRCodeView(APIView):
    permission_classes = [AllowAny]
    serializer_class = QRCodeRequestSerializer
    
    @extend_schema(
        summary="Generate QR code",
        request=QRCodeRequestSerializer,
        responses={201: QRCodeResponseSerializer}
    )
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

@extend_schema(tags=["QR Code"])
class GetQRCodeView(APIView):
    permission_classes = [AllowAny]
    serializer_class = QRCodeResponseSerializer
    
    @extend_schema(
        summary="Get QR code by content type and object ID",
        responses={200: QRCodeResponseSerializer}
    )
    def get(self, request, content_type, object_id):
        qr_code = QRCodeService.get_qr_code(content_type, object_id)
        
        if not qr_code:
            return Response({'error': 'QR Code not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'qr_code_id': str(qr_code.id),
            'qr_code_url': request.build_absolute_uri(qr_code.qr_code_image.url) if qr_code.qr_code_image else None,
            'qr_code_data': qr_code.qr_code_data
        })
