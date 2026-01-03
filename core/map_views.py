"""
Map-based provider search views
Leaflet/OpenStreetMap integration for finding doctors/hospitals
"""
from django.shortcuts import render
from django.db.models import Q, Avg
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from math import radians, cos, sin, asin, sqrt
from decimal import Decimal
from .models import Participant
from doctor.models import DoctorData


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points on earth (in kilometers)
    using Haversine formula
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def map_search_api(request):
    """
    API endpoint for map-based provider search
    Returns providers with coordinates for map display
    """
    # Get search parameters
    search_query = request.GET.get('search', '')
    specialty = request.GET.get('specialty', '')
    min_rating = request.GET.get('min_rating', 0)
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    radius = request.GET.get('radius', 50)  # Default 50km
    
    try:
        min_rating = float(min_rating)
        radius = float(radius)
    except (ValueError, TypeError):
        min_rating = 0
        radius = 50
    
    # Base query for doctors and hospitals with coordinates
    providers = Participant.objects.filter(
        role__in=['doctor', 'hospital'],
        is_active=True,
        is_verified=True,
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    # Apply filters
    if search_query:
        providers = providers.filter(
            Q(full_name__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    # Filter by specialty (for doctors)
    if specialty:
        doctor_ids = DoctorData.objects.filter(
            specialization__icontains=specialty
        ).values_list('participant_id', flat=True)
        providers = providers.filter(
            Q(uid__in=doctor_ids) | Q(role='hospital')
        )
    
    # Prepare results
    results = []
    
    for provider in providers:
        # Calculate distance if user location provided
        distance = None
        if lat and lng:
            try:
                user_lat = float(lat)
                user_lng = float(lng)
                distance = haversine_distance(
                    user_lat, user_lng,
                    provider.latitude, provider.longitude
                )
                
                # Skip if outside radius
                if distance > radius:
                    continue
                    
            except (ValueError, TypeError, AttributeError):
                pass
        
        # Get provider-specific data
        provider_data = {
            'id': str(provider.uid),
            'name': provider.full_name,
            'role': provider.role,
            'latitude': float(provider.latitude),
            'longitude': float(provider.longitude),
            'address': provider.address,
            'city': provider.city,
            'country': provider.country,
            'phone': provider.phone_number,
            'distance': round(distance, 2) if distance else None,
            'rating': 0,
            'review_count': 0,
            'specialty': None,
            'consultation_fee': None,
            'available_today': False
        }
        
        # Add doctor-specific data
        if provider.role == 'doctor' and hasattr(provider, 'doctor_data'):
            doctor_data = provider.doctor_data
            provider_data['specialty'] = doctor_data.specialization
            provider_data['consultation_fee'] = float(doctor_data.consultation_fee) if doctor_data.consultation_fee else None
            provider_data['rating'] = float(doctor_data.rating) if doctor_data.rating else 0
            provider_data['review_count'] = doctor_data.reviews_count or 0
            
            # Filter by minimum rating
            if provider_data['rating'] < min_rating:
                continue
        
        # Add hospital-specific data
        elif provider.role == 'hospital' and hasattr(provider, 'hospital_data'):
            hospital_data = provider.hospital_data
            provider_data['rating'] = float(hospital_data.rating) if hospital_data.rating else 0
            provider_data['review_count'] = hospital_data.reviews_count or 0
            
            # Filter by minimum rating
            if provider_data['rating'] < min_rating:
                continue
        
        results.append(provider_data)
    
    # Sort by distance if available, otherwise by rating
    if lat and lng:
        results.sort(key=lambda x: (x['distance'] if x['distance'] else float('inf')))
    else:
        results.sort(key=lambda x: x['rating'], reverse=True)
    
    return Response({
        'count': len(results),
        'providers': results
    })


def map_search_view(request):
    """
    Render map search page
    """
    # Get all unique specialties for filter
    specialties = DoctorData.objects.filter(
        participant__is_active=True,
        participant__is_verified=True
    ).values_list('specialization', flat=True).distinct()
    
    context = {
        'specialties': sorted([s for s in specialties if s]),
        'page_title': 'Recherche sur Carte'
    }
    
    return render(request, 'core/map_search.html', context)
