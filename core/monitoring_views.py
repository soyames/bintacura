"""
API endpoints for centralized monitoring and logging
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import serializers as drf_serializers
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from .centralized_logging import RegionalLogAggregator, HealthMonitor
from .security_config import SecurityConfig
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@extend_schema(
    summary="Receive logs from regional deployments",
    tags=["Monitoring"],
    request=inline_serializer(
        name='RegionalLogRequest',
        fields={
            'region': drf_serializers.CharField(),
            'level': drf_serializers.CharField(),
            'message': drf_serializers.CharField(),
            'timestamp': drf_serializers.DateTimeField(),
        }
    ),
    responses={
        200: inline_serializer(
            name='LogReceivedResponse',
            fields={'status': drf_serializers.CharField()}
        ),
        401: inline_serializer(
            name='UnauthorizedResponse',
            fields={'error': drf_serializers.CharField()}
        ),
    }
)
@api_view(['POST'])
def receive_regional_logs(request):
    """
    Central hub endpoint to receive logs from regional deployments
    Only accessible with valid API key
    """
    api_key = request.headers.get('X-API-Key')
    expected_key = getattr(settings, 'CENTRAL_HUB_API_KEY', None)
    
    if not expected_key or api_key != expected_key:
        return Response(
            {'error': 'Invalid API key'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    log_aggregator = RegionalLogAggregator()
    success = log_aggregator.receive_log(request.data)
    
    if success:
        return Response({'status': 'received'}, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': 'Failed to process log'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@extend_schema(
    summary="Receive health status from regional deployments",
    tags=["Monitoring"],
    request=inline_serializer(
        name='HealthStatusRequest',
        fields={
            'region': drf_serializers.CharField(),
            'status': drf_serializers.CharField(),
            'timestamp': drf_serializers.DateTimeField(),
        }
    ),
    responses={
        200: inline_serializer(
            name='HealthStatusReceivedResponse',
            fields={'status': drf_serializers.CharField()}
        ),
        401: inline_serializer(
            name='HealthUnauthorizedResponse',
            fields={'error': drf_serializers.CharField()}
        ),
    }
)
@api_view(['POST'])
def receive_health_status(request):
    """
    Central hub endpoint to receive health status from regional deployments
    """
    api_key = request.headers.get('X-API-Key')
    expected_key = getattr(settings, 'CENTRAL_HUB_API_KEY', None)
    
    if not expected_key or api_key != expected_key:
        return Response(
            {'error': 'Invalid API key'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    region = request.data.get('region', 'unknown')
    logger.info(f"Health status received from region: {region}", extra={
        'health_data': request.data
    })
    
    return Response({'status': 'received'}, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get current health status",
    tags=["Monitoring"],
    responses={200: OpenApiResponse(description="Health status data")}
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_health_status(request):
    """
    Get current health status of this deployment
    """
    monitor = HealthMonitor()
    health_status = monitor.get_health_status()
    return Response(health_status, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get current security configuration",
    tags=["Monitoring"],
    responses={200: OpenApiResponse(description="Security configuration")}
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_security_config(request):
    """
    Get current security configuration
    """
    security_config = SecurityConfig()
    config = security_config.get_config()
    return Response(config, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get region configuration info",
    tags=["Monitoring"],
    responses={200: OpenApiResponse(description="Region configuration")}
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_region_info(request):
    """
    Get information about current region configuration
    """
    from .region_config import get_region_config
    
    region_config = get_region_config()
    
    return Response({
        'region_code': region_config.region_code,
        'region_name': region_config.region_name,
        'database': region_config.database_config.get('NAME', 'N/A'),
        'payment_provider': region_config.payment_config.get('provider', 'N/A'),
        'features': region_config.feature_flags,
        'is_central_hub': region_config.is_central_hub
    }, status=status.HTTP_200_OK)
