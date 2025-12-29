from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import PatientData, DependentProfile
from .serializers import PatientDataSerializer, DependentProfileSerializer
from prescriptions.models import Prescription
from prescriptions.serializers import PrescriptionSerializer


class PatientDataViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for PatientData
    Authenticated users can only access their own patient data
    """
    queryset = PatientData.objects.all()
    serializer_class = PatientDataSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        # Users can only see their own patient data
        if self.request.user.role == "patient":
            return PatientData.objects.filter(participant=self.request.user)
        # Staff/admin can see all
        elif self.request.user.is_staff:
            return PatientData.objects.all()
        return PatientData.objects.none()


class DependentProfileViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for DependentProfile
    Patients can manage their own dependents
    """
    queryset = DependentProfile.objects.all()
    serializer_class = DependentProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        # Users can only see their own dependents
        if self.request.user.role == "patient":
            return DependentProfile.objects.filter(
                patient=self.request.user, is_active=True
            )
        # Staff/admin can see all
        elif self.request.user.is_staff:
            return DependentProfile.objects.all()
        return DependentProfile.objects.none()

    def perform_create(self, serializer):  # Perform create
        # Automatically set the patient to the current user
        serializer.save(patient=self.request.user)


class PrescriptionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"PrescriptionsAPIView called for user: {request.user.email}")
        logger.info(f"User role: {request.user.role}")

        if request.user.role != 'patient':
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        prescriptions = Prescription.objects.filter(patient=request.user).prefetch_related('items', 'items__medication', 'doctor')
        logger.info(f"Found {prescriptions.count()} prescriptions")

        serializer = PrescriptionSerializer(prescriptions, many=True, context={'request': request})
        return Response({'results': serializer.data}, status=status.HTTP_200_OK)

