"""
Queue Management API Views
Handles appointment booking with payment, queue assignment, and notifications

This is the SINGLE source for queue management views.
"""
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from appointments.models import Appointment, AppointmentQueue
from appointments.serializers import AppointmentBookingSerializer
from queue_management.services import QueueManagementService
from core.models import Participant, ProviderService, Transaction as CoreTransaction



class BookAppointmentWithQueueView(APIView):
    """
    Book appointment with payment and automatic queue assignment
    Generates receipt with queue number
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):  # Post
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
            return Response(
                {'error': 'Healthcare participant not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_queue_status(request, participant_id=None):
    """Get queue status for a participant (doctor/hospital)"""
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
