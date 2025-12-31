"""
Hospital Service Management Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from decimal import Decimal

from core.models import Participant
from hospital.service_models import HospitalService
from core.regional_service_helper import RegionalServiceHelper
from core.decorators import role_required


@login_required
@role_required('hospital')
@require_http_methods(["GET", "POST"])
def create_hospital_service(request):
    """Create a new hospital service with regional pricing"""
    
    hospital = request.user.participant
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get form data
                name = request.POST.get('name', '').strip()
                category = request.POST.get('category', '')
                description = request.POST.get('description', '').strip()
                price_str = request.POST.get('price', '0')
                duration = request.POST.get('duration_minutes', '')
                requires_appointment = request.POST.get('requires_appointment') == 'on'
                
                # Validate required fields
                if not name or not category:
                    messages.error(request, "Le nom et la catégorie sont requis")
                    return redirect('hospital:create_service')
                
                # Parse price (input in major units, store in cents)
                try:
                    price_major = Decimal(price_str)
                    price_cents = int(price_major * 100)
                except (ValueError, InvalidOperation):
                    messages.error(request, "Prix invalide")
                    return redirect('hospital:create_service')
                
                # Validate price
                is_valid, error_msg = RegionalServiceHelper.validate_service_price(
                    price_cents, category
                )
                if not is_valid:
                    messages.error(request, error_msg)
                    return redirect('hospital:create_service')
                
                # Get region and currency
                region_code = RegionalServiceHelper.get_participant_region(hospital)
                currency = RegionalServiceHelper.get_participant_currency(hospital)
                
                # Create service
                service = HospitalService.objects.create(
                    region_code=region_code,
                    hospital=hospital,
                    name=name,
                    category=category,
                    description=description,
                    price=price_cents,
                    currency=currency,
                    duration_minutes=int(duration) if duration else None,
                    requires_appointment=requires_appointment,
                    is_available=True,
                    is_active=True
                )
                
                messages.success(
                    request,
                    f"Service '{name}' créé avec succès. Prix: {RegionalServiceHelper.format_price_display(price_cents, currency)}"
                )
                return redirect('hospital:list_services')
                
        except Exception as e:
            messages.error(request, f"Erreur lors de la création: {str(e)}")
            return redirect('hospital:create_service')
    
    # GET request - show form
    context = {
        'categories': HospitalService.SERVICE_CATEGORY_CHOICES,
        'default_currency': RegionalServiceHelper.get_participant_currency(hospital),
        'region_code': RegionalServiceHelper.get_participant_region(hospital),
    }
    return render(request, 'hospital/service_create.html', context)


@login_required
@role_required('hospital')
def list_hospital_services(request):
    """List all services for this hospital"""
    hospital = request.user.participant
    services = HospitalService.objects.filter(hospital=hospital).order_by('-created_at')
    
    # Format prices for display
    for service in services:
        service.price_display = RegionalServiceHelper.format_price_display(
            service.price, service.currency
        )
    
    context = {
        'services': services,
    }
    return render(request, 'hospital/service_list.html', context)


@login_required
@role_required('hospital')
@require_http_methods(["GET", "POST"])
def edit_hospital_service(request, service_id):
    """Edit an existing hospital service"""
    hospital = request.user.participant
    service = get_object_or_404(HospitalService, id=service_id, hospital=hospital)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                service.name = request.POST.get('name', service.name).strip()
                service.category = request.POST.get('category', service.category)
                service.description = request.POST.get('description', '').strip()
                
                # Update price
                price_str = request.POST.get('price', '0')
                try:
                    price_major = Decimal(price_str)
                    service.price = int(price_major * 100)
                except:
                    messages.error(request, "Prix invalide")
                    return redirect('hospital:edit_service', service_id=service_id)
                
                duration = request.POST.get('duration_minutes', '')
                service.duration_minutes = int(duration) if duration else None
                service.requires_appointment = request.POST.get('requires_appointment') == 'on'
                service.is_available = request.POST.get('is_available') == 'on'
                
                service.save()
                
                messages.success(request, f"Service '{service.name}' mis à jour")
                return redirect('hospital:list_services')
                
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")
    
    # Convert price from cents to major units for form
    service.price_major = Decimal(service.price) / 100
    
    context = {
        'service': service,
        'categories': HospitalService.SERVICE_CATEGORY_CHOICES,
    }
    return render(request, 'hospital/service_edit.html', context)


@login_required
@role_required('hospital')
@require_http_methods(["POST"])
def delete_hospital_service(request, service_id):
    """Delete (deactivate) a hospital service"""
    hospital = request.user.participant
    service = get_object_or_404(HospitalService, id=service_id, hospital=hospital)
    
    service.is_active = False
    service.is_available = False
    service.save()
    
    messages.success(request, f"Service '{service.name}' désactivé")
    return redirect('hospital:list_services')
