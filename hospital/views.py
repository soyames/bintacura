from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from django.utils import timezone
from django.db import transaction
from django.db import models
from django.contrib.auth.hashers import make_password
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
import uuid
import secrets
import string
from .models import HospitalStaff, Bed, Admission, DepartmentTask
from .service_models import HospitalService
from core.models import Department, Participant
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


class HospitalStaffViewSet(viewsets.ModelViewSet):  # View for HospitalStaffSet operations
    serializer_class = HospitalStaffSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if self.request.user.role == 'hospital':
            return HospitalStaff.objects.filter(hospital=self.request.user).select_related('department')
        if getattr(self, 'swagger_fake_view', False):
            return HospitalStaff.objects.none()
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
        if self.request.user.role == 'hospital':
            return Bed.objects.filter(hospital=self.request.user).select_related('department')
        if getattr(self, 'swagger_fake_view', False):
            return Bed.objects.none()
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
        if self.request.user.role == 'hospital':
            return Admission.objects.filter(hospital=self.request.user).select_related(
                'patient', 'department', 'bed', 'admitting_doctor'
            )
        if getattr(self, 'swagger_fake_view', False):
            return Admission.objects.none()
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
        if self.request.user.role == 'hospital':
            return DepartmentTask.objects.filter(
                department__hospital=self.request.user
            ).select_related('department', 'assigned_to', 'created_by')
        if getattr(self, 'swagger_fake_view', False):
            return DepartmentTask.objects.none()
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
        if self.request.user.role == 'hospital':
            return Department.objects.filter(hospital=self.request.user).select_related('head_of_department')
        if getattr(self, 'swagger_fake_view', False):
            return Department.objects.none()
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
