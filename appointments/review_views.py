"""
Review system views for appointments
Handles creating, viewing, and responding to reviews
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Avg
from core.models import Review, Participant
from appointments.models import Appointment
from rest_framework import serializers


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.full_name', read_only=True)
    can_respond = serializers.SerializerMethodField()
    uid = serializers.UUIDField(read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'uid', 'reviewer', 'reviewer_name', 'reviewed_type', 'reviewed_id',
            'rating', 'service_type', 'review_text',
            'professionalism_rating', 'communication_rating', 'facility_rating',
            'wait_time_rating', 'value_rating',
            'appointment_id', 'is_verified', 'is_approved', 'is_featured',
            'provider_response', 'provider_responded_at',
            'created_at', 'updated_at', 'can_respond'
        ]
        read_only_fields = ['uid', 'reviewer', 'created_at', 'updated_at', 'provider_responded_at']
    
    def get_can_respond(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        # Provider can respond if they are the reviewed entity
        return str(request.user.uid) == str(obj.reviewed_id)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Review.objects.filter(is_approved=True)
        
        # Filter by provider
        provider_id = self.request.query_params.get('provider_id')
        if provider_id:
            queryset = queryset.filter(reviewed_id=provider_id)
        
        # Filter by reviewer (my reviews)
        if self.request.query_params.get('my_reviews') == 'true':
            queryset = queryset.filter(reviewer=user)
        
        # Filter by type
        reviewed_type = self.request.query_params.get('type')
        if reviewed_type:
            queryset = queryset.filter(reviewed_type=reviewed_type)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        # Set reviewer to current user
        serializer.save(reviewer=self.request.user)
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Provider responds to a review"""
        review = self.get_object()
        
        # Check if user is the reviewed provider
        if str(request.user.uid) != str(review.reviewed_id):
            return Response(
                {'error': 'Vous n\'êtes pas autorisé à répondre à cet avis'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        response_text = request.data.get('response')
        if not response_text:
            return Response(
                {'error': 'La réponse ne peut pas être vide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        review.provider_response = response_text
        from django.utils import timezone
        review.provider_responded_at = timezone.now()
        review.save()
        
        serializer = self.get_serializer(review)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get review statistics for a provider"""
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({'error': 'provider_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        
        reviews = Review.objects.filter(
            reviewed_id=provider_id,
            is_approved=True
        )
        
        stats = {
            'total_reviews': reviews.count(),
            'average_rating': reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
            'rating_distribution': {
                '5': reviews.filter(rating=5).count(),
                '4': reviews.filter(rating=4).count(),
                '3': reviews.filter(rating=3).count(),
                '2': reviews.filter(rating=2).count(),
                '1': reviews.filter(rating=1).count(),
            },
            'detailed_ratings': {
                'professionalism': reviews.aggregate(Avg('professionalism_rating'))['professionalism_rating__avg'] or 0,
                'communication': reviews.aggregate(Avg('communication_rating'))['communication_rating__avg'] or 0,
                'facility': reviews.aggregate(Avg('facility_rating'))['facility_rating__avg'] or 0,
                'wait_time': reviews.aggregate(Avg('wait_time_rating'))['wait_time_rating__avg'] or 0,
                'value': reviews.aggregate(Avg('value_rating'))['value_rating__avg'] or 0,
            }
        }
        
        return Response(stats)


@login_required
def leave_review_view(request, appointment_id):
    """Render review form for an appointment"""
    appointment = get_object_or_404(Appointment, uid=appointment_id, patient=request.user)
    
    # Check if already reviewed
    existing_review = Review.objects.filter(
        reviewer=request.user,
        appointment_id=appointment_id
    ).first()
    
    context = {
        'appointment': appointment,
        'existing_review': existing_review,
        'page_title': 'Laisser un Avis'
    }
    
    return render(request, 'appointments/leave_review.html', context)


@login_required
def reviews_list_view(request):
    """View all reviews for the current user (as provider)"""
    if request.user.role not in ['doctor', 'hospital', 'pharmacy', 'insurance_company']:
        return render(request, 'appointments/reviews_list.html', {
            'error': 'Seuls les prestataires peuvent voir cette page'
        })
    
    context = {
        'provider': request.user,
        'page_title': 'Mes Avis'
    }
    
    return render(request, 'appointments/reviews_list.html', context)


@login_required
def my_reviews_view(request):
    """View reviews given by the current user"""
    context = {
        'page_title': 'Mes Avis Donnés'
    }
    
    return render(request, 'appointments/my_reviews.html', context)
