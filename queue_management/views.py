"""
Queue Management API Views
Handles appointment booking with payment, queue assignment, and notifications

This is the SINGLE source for queue management views.
"""
import logging
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, serializers as drf_serializers
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter, inline_serializer, OpenApiTypes
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from appointments.models import Appointment, AppointmentQueue
from appointments.serializers import AppointmentBookingSerializer
from queue_management.services import QueueManagementService
from core.models import Participant, ProviderService, Transaction as CoreTransaction

logger = logging.getLogger(__name__)



@extend_schema(tags=["Queue Management"], summary="Book appointment with queue")
class BookAppointmentWithQueueView(APIView):
    """
    Book appointment with payment and automatic queue assignment
    Generates receipt with queue number
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentBookingSerializer
    
    @extend_schema(
        request=AppointmentBookingSerializer,
        responses={201: AppointmentBookingSerializer}
    )
    def post(self, request):  # Post
        logger.error(f"🔍 =============== BOOK APPOINTMENT DEBUG ===============")
        logger.error(f"   Logged-in user: {request.user.email}")
        logger.error(f"   User full name: {request.user.full_name}")
        logger.error(f"   User UID: {request.user.uid}")
        logger.error(f"   User role: {request.user.role}")
        logger.error(f"========================================================")
        
        if request.user.role != 'patient':
            return Response(
                {'error': 'Only patients can book appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = AppointmentBookingSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        
        try:
            # Get participant (doctor or hospital)
            service_participant = Participant.objects.get(uid=data['participant_id'])
            additional_service_ids = data.get('additional_service_ids', [])
            
            # Prepare appointment data based on participant role
            appointment_data = {
                'doctor': service_participant if service_participant.role == 'doctor' else None,
                'hospital': service_participant if service_participant.role == 'hospital' else None,
                'additional_services': additional_service_ids,
                'appointment_date': data['appointment_date'],
                'appointment_time': data['appointment_time'],
                'type': data['type'],
                'reason': data.get('reason', ''),
                'symptoms': data.get('symptoms', '')
            }
            
            # Book with payment and queue
            result = QueueManagementService.book_appointment_with_payment(
                patient=request.user,
                appointment_data=appointment_data,
                payment_method=data['payment_method']
            )
            
            # Get queue position
            queue_position = QueueManagementService.get_queue_position(
                result['appointment'].queue_entry.id
            )
            
            response_data = {
                'success': True,
                'message': 'Appointment booked successfully',
                'appointment_id': str(result['appointment'].id),
                'queue_number': result['queue_number'],
                'queue_position': queue_position,
                'estimated_wait_time': result['estimated_wait_time'],
                'payment_method': data['payment_method'],
                'payment_url': result.get('payment_url'),  # FedaPay payment URL for online payments
                'invoice_url': f'/patient/view-invoice/?transaction_id={result.get("transaction_id", "")}' if result.get("transaction_id") else None
            }
            
            if result.get('payment_result'):
                response_data['fee_details'] = result['payment_result']['fee_calculation']
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Participant.DoesNotExist:
            logger.exception("Healthcare participant not found")
            return Response(
                {'error': 'Healthcare participant not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.exception(f"Booking appointment failed: {str(e)}")
            return Response(
                {'error': f'Booking failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )





@extend_schema(
    summary="Call next patient in queue",
    tags=["Queue Management"],
    request=inline_serializer(
        name='CallNextPatientRequest',
        fields={'appointment_date': drf_serializers.DateField(required=False)}
    ),
    responses={
        200: inline_serializer(
            name='CallNextPatientResponse',
            fields={
                'success': drf_serializers.BooleanField(),
                'message': drf_serializers.CharField(),
                'patient_name': drf_serializers.CharField(),
                'queue_number': drf_serializers.IntegerField(),
                'appointment_id': drf_serializers.UUIDField(),
            }
        ),
        403: inline_serializer(
            name='CallNextPatientForbiddenResponse',
            fields={'error': drf_serializers.CharField()}
        ),
        404: inline_serializer(
            name='CallNextPatientNotFoundResponse',
            fields={
                'success': drf_serializers.BooleanField(),
                'message': drf_serializers.CharField()
            }
        ),
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def call_next_patient(request):
    """Provider calls next patient in queue"""
    if request.user.role not in ['doctor', 'hospital']:
        return Response(
            {'error': 'Only providers can call patients'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    appointment_date = request.data.get('appointment_date')
    
    result = QueueManagementService.call_next_patient(
        provider=request.user,
        appointment_date=appointment_date
    )
    
    if result['success']:
        return Response({
            'success': True,
            'message': result['message'],
            'patient_name': result['patient'].full_name,
            'queue_number': result['queue_entry'].queue_number,
            'appointment_id': str(result['appointment'].id)
        })
    else:
        return Response(
            {'success': False, 'message': result['message']},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    operation_id="get_my_queue_status",
    tags=["Queue Management"],
    summary="Get queue status for current participant",
    parameters=[
        OpenApiParameter(
            name='date',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description='Appointment date (YYYY-MM-DD)',
            required=False
        )
    ],
    responses={200: inline_serializer(
        name='MyQueueStatusResponse',
        fields={
            'queue_entries': drf_serializers.ListField(),
            'total_waiting': drf_serializers.IntegerField(),
        }
    )}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_queue_status(request, participant_id=None):
    """Get queue status for current participant (doctor/hospital)"""
    if participant_id is None:
        if request.user.role in ['doctor', 'hospital']:
            participant_id = str(request.user.uid)
        else:
            return Response(
                {'error': 'Participant ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    appointment_date = request.GET.get('date')
    
    try:
        status_data = QueueManagementService.get_participant_queue_status(
            participant_id,
            appointment_date
        )
        
        return Response(status_data)
        
    except Participant.DoesNotExist:
        return Response(
            {'error': 'Provider not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    operation_id="get_provider_queue_status",
    tags=["Queue Management"],
    summary="Get queue status for specific participant",
    parameters=[
        OpenApiParameter(
            name='participant_id',
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description='Participant UUID',
            required=True
        ),
        OpenApiParameter(
            name='date',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description='Appointment date (YYYY-MM-DD)',
            required=False
        )
    ],
    responses={200: inline_serializer(
        name='ProviderQueueStatusResponse',
        fields={
            'queue_entries': drf_serializers.ListField(),
            'total_waiting': drf_serializers.IntegerField(),
        }
    )}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_provider_queue_status(request, participant_id):
    """Get queue status for specific participant (doctor/hospital)"""
    appointment_date = request.GET.get('date')
    
    try:
        status_data = QueueManagementService.get_participant_queue_status(
            participant_id,
            appointment_date
        )
        
        return Response(status_data)
        
    except Participant.DoesNotExist:
        return Response(
            {'error': 'Provider not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    tags=["Queue Management"],
    summary="Complete appointment and update queue",
    responses={200: OpenApiResponse(description="Appointment completed")}
)
@extend_schema(
    summary="Complete appointment and update queue",
    tags=["Queue Management"],
    request=None,
    responses={
        200: inline_serializer(
            name='CompleteAppointmentResponse',
            fields={
                'success': drf_serializers.BooleanField(),
                'message': drf_serializers.CharField(),
                'duration_minutes': drf_serializers.IntegerField(),
            }
        ),
        403: inline_serializer(
            name='CompleteAppointmentUnauthorizedResponse',
            fields={'error': drf_serializers.CharField()}
        ),
        404: inline_serializer(
            name='CompleteAppointmentNotFoundResponse',
            fields={'error': drf_serializers.CharField()}
        ),
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_appointment_with_queue(request, appointment_id):
    """Complete appointment and update queue"""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        if appointment.provider != request.user:
            return Response(
                {'error': 'Unauthorized'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        result = QueueManagementService.complete_appointment(str(appointment_id))
        
        if result['success']:
            return Response({
                'success': True,
                'message': 'Appointment completed',
                'duration_minutes': result.get('duration_minutes', 0)
            })
        else:
            return Response(
                {'error': result.get('error')},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Appointment.DoesNotExist:
        return Response(
            {'error': 'Appointment not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    tags=["Queue Management"],
    summary="Get patient's position in queue",
    responses={200: OpenApiResponse(description="Queue position")}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_queue_position(request, appointment_id):
    """Get patient's position in queue"""
    try:
        appointment = Appointment.objects.get(
            id=appointment_id,
            patient=request.user
        )
        
        queue_entry = appointment.queue_entry
        position = QueueManagementService.get_queue_position(str(queue_entry.id))
        
        return Response(position)
        
    except Appointment.DoesNotExist:
        return Response(
            {'error': 'Appointment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except AttributeError:
        return Response(
            {'error': 'No queue entry found for this appointment'},
            status=status.HTTP_404_NOT_FOUND
        )
