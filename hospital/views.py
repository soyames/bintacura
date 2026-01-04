from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from django.utils import timezone
from django.db import transaction
from django.db import models
from django.contrib.auth.hashers import make_password
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
import uuid
import secrets
import string
from .models import HospitalStaff, Bed, Admission, DepartmentTask
from .service_models import HospitalService
from core.models import Department, Participant, MedicalEquipment
from core.serializers import ParticipantSerializer
from transport.models import TransportRequest
from transport.serializers import TransportRequestSerializer
from .serializers import (
    HospitalStaffSerializer, BedSerializer, AdmissionSerializer,
    DepartmentTaskSerializer, DepartmentSerializer
)


class HospitalQueueView(LoginRequiredMixin, TemplateView):  # View for HospitalQueue operations
    template_name = 'hospital/queue.html'
    
    def get_context_data(self, **kwargs):  # Get context data
        context = super().get_context_data(**kwargs)
        context['page_title'] = "File d'attente"
        return context


class HospitalTransportDashboardView(LoginRequiredMixin, TemplateView):
    """Hospital transport requests dashboard"""
    template_name = 'hospital/transport_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Demandes de Transport"
        
        # Get transport requests for this hospital's region
        if self.request.user.role == 'hospital':
            hospital = self.request.user
            from django.db.models import Q
            from django.utils import timezone
            from datetime import timedelta
            
            # Auto-release expired accepted requests (30 min timeout)
            expired_time = timezone.now() - timedelta(minutes=30)
            TransportRequest.objects.filter(
                status='accepted',
                payment_status='pending',
                accepted_at__lt=expired_time
            ).update(
                status='pending',
                assigned_hospital=None,
                accepted_at=None
            )
            
            # Get ALL pending requests (not yet accepted by anyone OR by this hospital)
            all_requests = TransportRequest.objects.filter(
                Q(status='pending', assigned_hospital__isnull=True) |
                Q(status='accepted', assigned_hospital=hospital)
            ).select_related('patient').order_by('-created_at')
            
            # Get accepted requests by THIS hospital (waiting for payment or staff assignment)
            my_accepted_requests = TransportRequest.objects.filter(
                assigned_hospital=hospital,
                status='accepted'
            ).select_related('patient').order_by('-created_at')
            
            # Get active requests assigned to this hospital (driver assigned, in progress)
            active_requests = TransportRequest.objects.filter(
                assigned_hospital=hospital,
                status__in=['driver_assigned', 'en_route', 'arrived', 'in_transit']
            ).select_related('patient').order_by('-created_at')
            
            # Get completed requests for this hospital
            completed_requests = TransportRequest.objects.filter(
                assigned_hospital_id=hospital.uid,
                status__in=['completed', 'cancelled']
            ).select_related('patient').order_by('-created_at')[:10]
            
            # Get drivers for staff assignment
            from hospital.models import HospitalStaff
            drivers = HospitalStaff.objects.filter(
                hospital=hospital,
                role='DRIVER',
                is_active=True
            ).select_related('participant')
            
            # Get vehicles for this hospital (hardcoded for now - can be moved to database later)
            import json
            vehicles = [
                {'id': 'AMB-101-VTC', 'name': 'Ambulance A-101', 'plate': 'AMB-101-VTC', 'type': 'ambulance'},
                {'id': 'AMB-102-VTC', 'name': 'Ambulance A-102', 'plate': 'AMB-102-VTC', 'type': 'ambulance'},
                {'id': 'AMB-103-VTC', 'name': 'Ambulance A-103', 'plate': 'AMB-103-VTC', 'type': 'ambulance'},
            ]
            
            context['pending_requests'] = all_requests
            context['my_accepted_requests'] = my_accepted_requests
            context['active_requests'] = active_requests
            context['completed_requests'] = completed_requests
            context['hospital'] = hospital
            context['drivers'] = drivers
            context['vehicles'] = json.dumps(vehicles)
        
        return context


class HospitalStaffViewSet(viewsets.ModelViewSet):  # View for HospitalStaffSet operations
    serializer_class = HospitalStaffSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return HospitalStaff.objects.none()
        if self.request.user.role == 'hospital':
            return HospitalStaff.objects.filter(hospital=self.request.user).select_related('department')
        return HospitalStaff.objects.none()

    def perform_create(self, serializer):  # Perform create
        with transaction.atomic():
            staff_data = serializer.validated_data

            alphabet = string.ascii_letters + string.digits
            temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))

            # Determine if this is a doctor staff member
            is_doctor = staff_data['role'] == 'doctor'
            # Staff members use the provider's role (hospital), not separate staff role
            participant_role = 'doctor' if is_doctor else 'hospital'

            user_participant = Participant.objects.create(
                email=staff_data['email'],
                phone_number=staff_data['phone_number'],
                full_name=staff_data['full_name'],
                role=participant_role,
                password=make_password(temp_password),
                is_active=True,
                affiliated_provider_id=self.request.user.uid,  # Use uid not id
                staff_role=staff_data['role'],
                department_id=str(staff_data.get('department').id) if staff_data.get('department') else '',
            )

            staff = serializer.save(
                hospital=self.request.user,
                staff_participant=user_participant
            )

            # If this is a doctor, create a locked affiliation
            if is_doctor:
                from doctor.models import DoctorAffiliation
                DoctorAffiliation.objects.create(
                    doctor=user_participant,
                    hospital=self.request.user,
                    is_primary=True,
                    is_locked=True,
                    department_id=str(staff_data.get('department').id) if staff_data.get('department') else ''
                )

    @action(detail=False, methods=['get'])
    def by_department(self, request):  # By department
        department_id = request.query_params.get('department_id')
        if department_id:
            staff = self.get_queryset().filter(department_id=department_id, is_active=True)
            serializer = self.get_serializer(staff, many=True)
            return Response(serializer.data)
        return Response({'error': 'department_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def by_role(self, request):  # By role
        role = request.query_params.get('role')
        if role:
            staff = self.get_queryset().filter(role=role, is_active=True)
            serializer = self.get_serializer(staff, many=True)
            return Response(serializer.data)
        return Response({'error': 'role required'}, status=status.HTTP_400_BAD_REQUEST)


class BedViewSet(viewsets.ModelViewSet):  # View for BedSet operations
    serializer_class = BedSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return Bed.objects.none()
        if self.request.user.role == 'hospital':
            return Bed.objects.filter(hospital=self.request.user).select_related('department')
        return Bed.objects.none()

    def perform_create(self, serializer):  # Perform create
        serializer.save(hospital=self.request.user)

    @action(detail=False, methods=['get'])
    def available(self, request):  # Available
        department_id = request.query_params.get('department_id')
        queryset = self.get_queryset().filter(status='available')
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def update_status(self, request, pk=None):  # Update status
        # Use select_for_update to prevent race conditions on bed status
        bed = Bed.objects.select_for_update().get(pk=pk)
        new_status = request.data.get('status')

        if new_status in dict(Bed.STATUS_CHOICES):
            bed.status = new_status
            if new_status == 'available':
                bed.last_cleaned = timezone.now()
            bed.save()

            department = bed.department
            if department:
                occupied_count = Bed.objects.filter(
                    department=department,
                    status='occupied'
                ).count()
                department.occupied_beds = occupied_count
                department.save()

            return Response({'status': 'success', 'message': 'Statut du lit mis à jour'})
        return Response({'error': 'Statut invalide'}, status=status.HTTP_400_BAD_REQUEST)


class AdmissionViewSet(viewsets.ModelViewSet):  # View for AdmissionSet operations
    serializer_class = AdmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return Admission.objects.none()
        if self.request.user.role == 'hospital':
            return Admission.objects.filter(hospital=self.request.user).select_related(
                'patient', 'department', 'bed', 'admitting_doctor'
            )
        return Admission.objects.none()

    @transaction.atomic
    def perform_create(self, serializer):  # Perform create
        admission_number = f"ADM-{uuid.uuid4().hex[:10].upper()}"
        admission = serializer.save(hospital=self.request.user, admission_number=admission_number)

        if admission.bed:
            # Use select_for_update to prevent race conditions on bed allocation
            bed = Bed.objects.select_for_update().get(pk=admission.bed.pk)
            bed.status = 'occupied'
            bed.save()

            if admission.department:
                admission.department.occupied_beds = Bed.objects.filter(
                    department=admission.department,
                    status='occupied'
                ).count()
                admission.department.save()

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def discharge(self, request, pk=None):  # Discharge
        # Use select_for_update to prevent race conditions
        admission = Admission.objects.select_for_update().get(pk=pk)

        if admission.status == 'discharged':
            return Response({'error': 'Patient déjà sorti'}, status=status.HTTP_400_BAD_REQUEST)

        admission.status = 'discharged'
        admission.actual_discharge_date = timezone.now()
        admission.discharge_summary = request.data.get('discharge_summary', '')
        admission.discharge_instructions = request.data.get('discharge_instructions', '')
        admission.follow_up_required = request.data.get('follow_up_required', False)
        admission.follow_up_date = request.data.get('follow_up_date')
        admission.save()

        if admission.bed:
            # Use select_for_update to prevent race conditions on bed status
            bed = Bed.objects.select_for_update().get(pk=admission.bed.pk)
            bed.status = 'available'
            bed.last_cleaned = timezone.now()
            bed.save()

            if admission.department:
                admission.department.occupied_beds = Bed.objects.filter(
                    department=admission.department,
                    status='occupied'
                ).count()
                admission.department.save()

        return Response({'status': 'success', 'message': 'Patient sorti avec succès'})

    @action(detail=False, methods=['get'])
    def active_admissions(self, request):  # Active admissions
        admissions = self.get_queryset().filter(status='admitted')
        serializer = self.get_serializer(admissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_department(self, request):  # By department
        department_id = request.query_params.get('department_id')
        if department_id:
            admissions = self.get_queryset().filter(department_id=department_id)
            serializer = self.get_serializer(admissions, many=True)
            return Response(serializer.data)
        return Response({'error': 'department_id required'}, status=status.HTTP_400_BAD_REQUEST)


class DepartmentTaskViewSet(viewsets.ModelViewSet):  # View for DepartmentTaskSet operations
    serializer_class = DepartmentTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return DepartmentTask.objects.none()
        if self.request.user.role == 'hospital':
            return DepartmentTask.objects.filter(
                department__hospital=self.request.user
            ).select_related('department', 'assigned_to', 'created_by')
        return DepartmentTask.objects.none()

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):  # Complete
        task = self.get_object()
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.notes = request.data.get('notes', task.notes)
        task.save()
        return Response({'status': 'success', 'message': 'Tâche complétée'})

    @action(detail=False, methods=['get'])
    def by_staff(self, request):  # By staff
        staff_id = request.query_params.get('staff_id')
        if staff_id:
            tasks = self.get_queryset().filter(assigned_to_id=staff_id)
            serializer = self.get_serializer(tasks, many=True)
            return Response(serializer.data)
        return Response({'error': 'staff_id required'}, status=status.HTTP_400_BAD_REQUEST)


class DepartmentViewSet(viewsets.ModelViewSet):  # View for DepartmentSet operations
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if getattr(self, 'swagger_fake_view', False):
            return Department.objects.none()
        if self.request.user.role == 'hospital':
            return Department.objects.filter(hospital=self.request.user).select_related('head_of_department')
        return Department.objects.none()

    def perform_create(self, serializer):  # Perform create
        serializer.save(hospital=self.request.user)

    @action(detail=False, methods=['get'])
    def with_stats(self, request):  # With stats
        departments = self.get_queryset()
        data = []
        for dept in departments:
            staff_count = HospitalStaff.objects.filter(department=dept, is_active=True).count()
            active_admissions = Admission.objects.filter(department=dept, status='admitted').count()

            data.append({
                'id': str(dept.id),
                'name': dept.name,
                'description': dept.description,
                'total_beds': dept.total_beds,
                'occupied_beds': dept.occupied_beds,
                'available_beds': dept.total_beds - dept.occupied_beds,
                'staff_count': staff_count,
                'active_admissions': active_admissions,
                'head_of_department': dept.head_of_department.full_name if dept.head_of_department else None,
                'is_active': dept.is_active
            })

        return Response(data)


@extend_schema(tags=["Hospital Analytics"])
class HospitalAnalyticsViewSet(viewsets.ViewSet):
    """AI-powered hospital operations analytics"""
    permission_classes = [IsAuthenticated]
    serializer_class = ParticipantSerializer

    @action(detail=False, methods=['get'])
    def ai_bed_occupancy(self, request):
        """AI-powered bed occupancy prediction"""
        from .ai_insights import HospitalAI

        hospital = request.user
        if hospital.role != 'hospital':
            return Response({'error': 'Only hospital accounts can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)

        days_forward = int(request.query_params.get('days', 7))

        if days_forward > 30:
            return Response({'error': 'Maximum forecast period is 30 days'}, status=status.HTTP_400_BAD_REQUEST)

        forecast = HospitalAI.predict_bed_occupancy(hospital, days_forward=days_forward)

        return Response(forecast)

    @action(detail=False, methods=['get'])
    def ai_staff_scheduling(self, request):
        """AI-powered staff scheduling optimization"""
        from .ai_insights import HospitalAI

        hospital = request.user
        if hospital.role != 'hospital':
            return Response({'error': 'Only hospital accounts can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)

        department_id = request.query_params.get('department')
        days_forward = int(request.query_params.get('days', 7))

        department = None
        if department_id:
            try:
                department = Department.objects.get(id=department_id, hospital=hospital)
            except Department.DoesNotExist:
                return Response({'error': 'Department not found'}, status=status.HTTP_404_NOT_FOUND)

        analysis = HospitalAI.optimize_staff_scheduling(
            hospital=hospital,
            department=department,
            days_forward=days_forward
        )

        return Response(analysis)

    @action(detail=False, methods=['get'])
    def ai_maintenance_prediction(self, request):
        """AI-powered equipment maintenance prediction"""
        from .ai_insights import HospitalAI

        hospital = request.user
        if hospital.role != 'hospital':
            return Response({'error': 'Only hospital accounts can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)

        prediction = HospitalAI.predict_equipment_maintenance(hospital)

        return Response(prediction)

    @action(detail=False, methods=['get'])
    def ai_insights_overview(self, request):
        """Get all hospital AI insights in one response"""
        from .ai_insights import HospitalAI

        hospital = request.user
        if hospital.role != 'hospital':
            return Response({'error': 'Only hospital accounts can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)

        insights = HospitalAI.get_hospital_insights(hospital)

        return Response({
            'hospital': hospital.full_name,
            'total_insights': len(insights),
            'high_priority_count': len([i for i in insights if i['priority'] == 'high']),
            'medium_priority_count': len([i for i in insights if i['priority'] == 'medium']),
            'low_priority_count': len([i for i in insights if i['priority'] == 'low']),
            'insights': insights,
            'generated_at': timezone.now()
        })


class HospitalServiceViewSet(viewsets.ModelViewSet):
    """CRUD operations for hospital services with currency conversion"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role == 'hospital':
            return HospitalService.objects.filter(hospital=self.request.user)
        if getattr(self, 'swagger_fake_view', False):
            return HospitalService.objects.none()
        return HospitalService.objects.none()
    
    @transaction.atomic
    def perform_create(self, serializer):
        from currency_converter.utils import convert_to_xof
        
        hospital = self.request.user
        if not hospital.is_verified:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Votre compte doit être vérifié pour créer des services")
        
        price_input = self.request.data.get('price', 0)
        currency_input = self.request.data.get('currency', 'XOF')
        
        price_in_xof_cents = convert_to_xof(price_input, currency_input)
        
        serializer.save(
            hospital=hospital,
            price=price_in_xof_cents,
            currency='XOF',
            region_code=hospital.region_code or 'global'
        )
    
    @transaction.atomic
    def perform_update(self, serializer):
        from currency_converter.utils import convert_to_xof
        
        if 'price' in self.request.data:
            price_input = self.request.data.get('price', 0)
            currency_input = self.request.data.get('currency', 'XOF')
            price_in_xof_cents = convert_to_xof(price_input, currency_input)
            serializer.save(price=price_in_xof_cents, currency='XOF')
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category = request.query_params.get('category')
        if category:
            services = self.get_queryset().filter(category=category, is_active=True)
            from rest_framework.serializers import ModelSerializer
            
            class ServiceSerializer(ModelSerializer):
                class Meta:
                    model = HospitalService
                    fields = '__all__'
            
            serializer = ServiceSerializer(services, many=True)
            return Response(serializer.data)
        return Response({'error': 'category required'}, status=status.HTTP_400_BAD_REQUEST)


# Transport Request API Endpoints
from communication.models import Notification


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transport_requests(request):
    """Get transport requests for the hospital's region"""
    if request.user.role != 'hospital':
        return Response({'error': 'Only hospitals can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
    
    hospital = request.user
    status_filter = request.GET.get('status', 'pending')
    
    if status_filter == 'pending':
        requests = TransportRequest.objects.filter(
            status='pending',
            pickup_address__icontains=hospital.region
        ).select_related('patient').order_by('-created_at')
    elif status_filter == 'accepted':
        requests = TransportRequest.objects.filter(
            assigned_hospital=hospital,
            status__in=['driver_assigned', 'en_route', 'arrived', 'in_transit']
        ).select_related('patient').order_by('-created_at')
    elif status_filter == 'completed':
        requests = TransportRequest.objects.filter(
            assigned_hospital=hospital,
            status__in=['completed', 'cancelled']
        ).select_related('patient').order_by('-created_at')[:20]
    else:
        requests = TransportRequest.objects.filter(
            assigned_hospital=hospital
        ).select_related('patient').order_by('-created_at')
    
    serializer = TransportRequestSerializer(requests, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def accept_transport_request(request, request_id):
    """Step 1: Accept/claim a transport request - locks it for this hospital ONLY"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"✅ Accept request called for {request_id} by {request.user.email}")
    
    if request.user.role != 'hospital':
        logger.warning(f"Non-hospital user {request.user.email} tried to accept request")
        return Response({'error': 'Seuls les hôpitaux peuvent accepter les demandes'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        with transaction.atomic():
            # Lock ONLY this specific request by id
            transport_request = TransportRequest.objects.select_for_update().get(id=request_id)
            logger.info(f"Found request {request_id}, current status: {transport_request.status}, patient: {transport_request.patient.full_name}")
            
            if transport_request.status != 'pending':
                logger.warning(f"Request {request_id} is not pending, status: {transport_request.status}")
                return Response({
                    'error': 'Cette demande a déjà été acceptée par un autre hôpital'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if transport_request.assigned_hospital:
                logger.warning(f"Request {request_id} already assigned to {transport_request.assigned_hospital.full_name}")
                return Response({
                    'error': f'Cette demande a déjà été acceptée par {transport_request.assigned_hospital.full_name}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # STEP 1: Lock the request to this hospital
            transport_request.assigned_hospital_id = request.user.uid
            transport_request.status = 'accepted'
            transport_request.accepted_at = timezone.now()
            
            # Save ONLY these fields
            transport_request.save(update_fields=[
                'assigned_hospital_id', 'status', 'accepted_at', 'updated_at'
            ])
            logger.info(f"✅ Request {request_id} ACCEPTED by {request.user.full_name}. Status: {transport_request.status}")
            
            # Send notification to patient
            from communication.models import Notification
            Notification.objects.create(
                recipient=transport_request.patient,
                title="Demande de Transport Acceptée",
                message=f"L'hôpital {request.user.full_name} a accepté votre demande de transport du {transport_request.scheduled_pickup_time.strftime('%d/%m/%Y à %H:%M')}. "
                       f"Le personnel sera assigné sous peu.",
                notification_type='system',
                metadata={'transport_request_id': str(transport_request.id), 'priority': 'high'}
            )
            logger.info("Patient notification sent")
            
            from transport.serializers import TransportRequestSerializer
            serializer = TransportRequestSerializer(transport_request)
            return Response({
                'message': 'Transport accepté avec succès. Veuillez maintenant assigner le personnel.',
                'request': serializer.data
            })
        
    except TransportRequest.DoesNotExist:
        logger.error(f"Request {request_id} not found")
        return Response({'error': 'Demande non trouvée'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Unexpected error accepting request {request_id}: {e}")
        return Response({'error': f'Erreur inattendue: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def assign_staff_to_transport(request, request_id):
    """Step 2: Assign staff (driver & vehicle) to an accepted transport request"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Assign staff called for {request_id} by {request.user.email}")
    
    if request.user.role != 'hospital':
        logger.warning(f"Non-hospital user tried to assign staff")
        return Response({'error': 'Seuls les hôpitaux peuvent assigner du personnel'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        with transaction.atomic():
            transport_request = TransportRequest.objects.select_for_update().get(id=request_id)
            
            # Verify this hospital has accepted the request
            if transport_request.assigned_hospital != request.user:
                return Response({
                    'error': 'Vous ne pouvez assigner du personnel qu\'aux demandes que vous avez acceptées'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Verify status is 'accepted' (not already assigned)
            if transport_request.status not in ['accepted', 'driver_assigned']:
                return Response({
                    'error': f'Cette demande ne peut plus être modifiée (statut: {transport_request.get_status_display()})'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get assignment data
            driver_id = request.data.get('driver_id')
            vehicle_id = request.data.get('vehicle_id')
            notes = request.data.get('notes', '')
            
            logger.info(f"Assignment data: driver={driver_id}, vehicle={vehicle_id}")
            
            # Assign driver if provided
            if driver_id:
                try:
                    driver = HospitalStaff.objects.get(id=driver_id, hospital=request.user, is_active=True)
                    transport_request.driver_id = driver.staff_participant.uid
                    transport_request.driver_name = driver.full_name
                    transport_request.driver_phone = driver.phone_number
                    logger.info(f"Driver assigned: {driver.full_name}")
                except HospitalStaff.DoesNotExist:
                    logger.error(f"Driver {driver_id} not found")
                    return Response({'error': 'Chauffeur non trouvé'}, status=status.HTTP_404_NOT_FOUND)
            
            # Assign vehicle if provided
            if vehicle_id:
                transport_request.vehicle_number = vehicle_id
                logger.info(f"Vehicle assigned: {vehicle_id}")
            
            # Add assignment notes
            if notes:
                current_notes = transport_request.patient_notes or ''
                transport_request.patient_notes = f"{current_notes}\n\nNotes d'assignation: {notes}".strip()
            
            # Update status to driver_assigned
            transport_request.status = 'driver_assigned'
            
            # Save with specific fields
            transport_request.save(update_fields=[
                'driver_id', 'driver_name', 'driver_phone',
                'vehicle_number', 'patient_notes', 'status', 'updated_at'
            ])
            logger.info(f"✅ Staff assigned to request {request_id}. Status: {transport_request.status}")
            
            # Notify patient about driver assignment
            from communication.models import Notification
            Notification.objects.create(
                recipient=transport_request.patient,
                title="Personnel Assigné à Votre Transport",
                message=f"L'hôpital {request.user.full_name} a assigné le chauffeur {transport_request.driver_name} "
                       f"pour votre transport du {transport_request.scheduled_pickup_time.strftime('%d/%m/%Y à %H:%M')}.",
                notification_type='system',
                metadata={'transport_request_id': str(transport_request.id), 'driver_name': transport_request.driver_name}
            )
            
            # Notify driver
            if driver_id:
                try:
                    Notification.objects.create(
                        recipient=driver.staff_participant,
                        title="Nouvelle Mission de Transport",
                        message=f"Vous avez été assigné à une mission de transport pour {transport_request.patient.full_name}. "
                               f"Départ: {transport_request.pickup_address}. Heure: {transport_request.scheduled_pickup_time.strftime('%H:%M')}",
                        notification_type='system',
                        metadata={'transport_request_id': str(transport_request.id), 'patient_name': transport_request.patient.full_name}
                    )
                    logger.info("Driver notification sent")
                except Exception as e:
                    logger.error(f"Error sending driver notification: {e}")
            
            from transport.serializers import TransportRequestSerializer
            serializer = TransportRequestSerializer(transport_request)
            return Response({
                'message': 'Personnel assigné avec succès',
                'request': serializer.data
            })
            
    except TransportRequest.DoesNotExist:
        logger.error(f"Request {request_id} not found")
        return Response({'error': 'Demande non trouvée'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Unexpected error assigning staff to {request_id}: {e}")
        return Response({'error': f'Erreur inattendue: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def transfer_transport_request(request, request_id):
    """Transfer a transport request to another hospital or transport service"""
    if request.user.role != 'hospital':
        return Response({'error': 'Only hospitals can transfer requests'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        transport_request = TransportRequest.objects.select_for_update().get(id=request_id)
        target_hospital_id = request.data.get('target_hospital_id')
        transfer_notes = request.data.get('notes', '')
        
        # Verify this hospital has accepted the request
        if transport_request.assigned_hospital != request.user:
            return Response({
                'error': 'Vous ne pouvez transférer que les demandes que vous avez acceptées'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not target_hospital_id:
            return Response({'error': 'target_hospital_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get target hospital
        try:
            target_hospital = Participant.objects.get(uid=target_hospital_id, role='hospital')
        except Participant.DoesNotExist:
            return Response({'error': 'Hôpital cible non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        
        # Reset to pending and clear assignment
        old_hospital = transport_request.assigned_hospital
        transport_request.assigned_hospital = None
        transport_request.status = 'pending'
        transport_request.transfer_history = transport_request.transfer_history or []
        transport_request.transfer_history.append({
            'from_hospital': str(old_hospital.uid),
            'from_hospital_name': old_hospital.full_name,
            'to_hospital': str(target_hospital.uid),
            'to_hospital_name': target_hospital.full_name,
            'transferred_at': timezone.now().isoformat(),
            'notes': transfer_notes
        })
        transport_request.save()
        
        # Notify target hospital
        from communication.models import Notification
        Notification.objects.create(
            recipient=target_hospital,
            title="Demande de Transport Transférée",
            message=f"L'hôpital {old_hospital.full_name} vous a transféré une demande de transport pour {transport_request.patient.full_name}. Notes: {transfer_notes}",
            notification_type='system',
            metadata={'transport_request_id': str(transport_request.id), 'priority': 'high', 'transfer_notes': transfer_notes}
        )
        
        # Notify patient
        Notification.objects.create(
            recipient=transport_request.patient,
            title="Demande de Transport Transférée",
            message=f"Votre demande de transport a été transférée de {old_hospital.full_name} à {target_hospital.full_name}.",
            notification_type='system',
            metadata={'transport_request_id': str(transport_request.id), 'priority': 'medium', 'old_hospital': old_hospital.full_name, 'new_hospital': target_hospital.full_name}
        )
        
        from transport.serializers import TransportRequestSerializer
        serializer = TransportRequestSerializer(transport_request)
        return Response({
            'message': f'Demande transférée avec succès à {target_hospital.full_name}',
            'request': serializer.data
        })
        
    except TransportRequest.DoesNotExist:
        return Response({'error': 'Demande non trouvée'}, status=status.HTTP_404_NOT_FOUND)


class HospitalEquipmentView(LoginRequiredMixin, TemplateView):
    """Hospital equipment management view"""
    template_name = 'hospital/equipment.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Gestion des Équipements"
        
        if self.request.user.role == 'hospital':
            hospital = self.request.user
            
            # Get all equipment for this hospital
            equipment_list = MedicalEquipment.objects.filter(
                hospital=hospital,
                is_deleted=False
            ).order_by('-created_at')
            
            context['equipment_list'] = equipment_list
            context['total_equipment'] = equipment_list.count()
            context['available_count'] = equipment_list.filter(status='available').count()
            context['in_use_count'] = equipment_list.filter(status='in_use').count()
            context['maintenance_count'] = equipment_list.filter(status='maintenance').count()
            
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle equipment CRUD operations"""
        import json
        
        if request.user.role != 'hospital':
            return JsonResponse({'success': False, 'message': 'Non autorisé'}, status=403)
        
        try:
            data = json.loads(request.body)
            action = data.get('action')
            hospital = request.user
            
            if action == 'create':
                equipment = MedicalEquipment.objects.create(
                    hospital=hospital,
                    name=data.get('name'),
                    category=data.get('category'),
                    manufacturer=data.get('manufacturer', ''),
                    model_number=data.get('model_number', ''),
                    location=data.get('location', ''),
                    department=data.get('department', ''),
                    notes=data.get('notes', ''),
                    status=data.get('status', 'available'),
                    is_active=True
                )
                return JsonResponse({'success': True, 'message': 'Équipement créé avec succès'})
            
            elif action == 'update':
                equipment_id = data.get('equipment_id')
                equipment = MedicalEquipment.objects.get(id=equipment_id, hospital=hospital, is_deleted=False)
                
                equipment.name = data.get('name', equipment.name)
                equipment.category = data.get('category', equipment.category)
                equipment.location = data.get('location', equipment.location)
                equipment.department = data.get('department', equipment.department)
                equipment.status = data.get('status', equipment.status)
                equipment.notes = data.get('notes', equipment.notes)
                equipment.save()
                
                return JsonResponse({'success': True, 'message': 'Équipement mis à jour avec succès'})
            
            elif action == 'delete':
                equipment_id = data.get('equipment_id')
                equipment = MedicalEquipment.objects.get(id=equipment_id, hospital=hospital, is_deleted=False)
                equipment.is_deleted = True
                equipment.save()
                
                return JsonResponse({'success': True, 'message': 'Équipement supprimé avec succès'})
            
            else:
                return JsonResponse({'success': False, 'message': 'Action non reconnue'}, status=400)
                
        except MedicalEquipment.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Équipement non trouvé'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
