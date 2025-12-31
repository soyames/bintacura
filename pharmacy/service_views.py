"""
Pharmacy Service Management Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_http_methods
from decimal import Decimal

from core.models import Participant
from pharmacy.service_models import PharmacyService
from core.regional_service_helper import RegionalServiceHelper
from core.decorators import role_required


@login_required
@role_required('pharmacy')
@require_http_methods(["GET", "POST"])
def create_pharmacy_service(request):
    """Create a new pharmacy service with regional pricing"""
    
    pharmacy = request.user.participant
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                name = request.POST.get('name', '').strip()
                category = request.POST.get('category', '')
                description = request.POST.get('description', '').strip()
                price_str = request.POST.get('price', '0')
                duration = request.POST.get('duration_minutes', '')
                requires_appointment = request.POST.get('requires_appointment') == 'on'
                
                if not name or not category:
                    messages.error(request, "Le nom et la catégorie sont requis")
                    return redirect('pharmacy:create_service')
                
                try:
                    price_major = Decimal(price_str)
                    price_cents = int(price_major * 100)
                except:
                    messages.error(request, "Prix invalide")
                    return redirect('pharmacy:create_service')
                
                is_valid, error_msg = RegionalServiceHelper.validate_service_price(
                    price_cents, 'medication'
                )
                if not is_valid:
                    messages.error(request, error_msg)
                    return redirect('pharmacy:create_service')
                
                region_code = RegionalServiceHelper.get_participant_region(pharmacy)
                currency = RegionalServiceHelper.get_participant_currency(pharmacy)
                
                service = PharmacyService.objects.create(
                    region_code=region_code,
                    pharmacy=pharmacy,
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
                return redirect('pharmacy:list_services')
                
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")
            return redirect('pharmacy:create_service')
    
    context = {
        'categories': PharmacyService.SERVICE_CATEGORY_CHOICES,
        'default_currency': RegionalServiceHelper.get_participant_currency(pharmacy),
        'region_code': RegionalServiceHelper.get_participant_region(pharmacy),
    }
    return render(request, 'pharmacy/service_create.html', context)


@login_required
@role_required('pharmacy')
def list_pharmacy_services(request):
    """List all services for this pharmacy"""
    pharmacy = request.user.participant
    services = PharmacyService.objects.filter(pharmacy=pharmacy).order_by('-created_at')
    
    for service in services:
        service.price_display = RegionalServiceHelper.format_price_display(
            service.price, service.currency
        )
    
    context = {'services': services}
    return render(request, 'pharmacy/service_list.html', context)


@login_required
@role_required('pharmacy')
@require_http_methods(["GET", "POST"])
def edit_pharmacy_service(request, service_id):
    """Edit an existing pharmacy service"""
    pharmacy = request.user.participant
    service = get_object_or_404(PharmacyService, id=service_id, pharmacy=pharmacy)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                service.name = request.POST.get('name', service.name).strip()
                service.category = request.POST.get('category', service.category)
                service.description = request.POST.get('description', '').strip()
                
                price_str = request.POST.get('price', '0')
                try:
                    price_major = Decimal(price_str)
                    service.price = int(price_major * 100)
                except:
                    messages.error(request, "Prix invalide")
                    return redirect('pharmacy:edit_service', service_id=service_id)
                
                duration = request.POST.get('duration_minutes', '')
                service.duration_minutes = int(duration) if duration else None
                service.requires_appointment = request.POST.get('requires_appointment') == 'on'
                service.is_available = request.POST.get('is_available') == 'on'
                
                service.save()
                
                messages.success(request, f"Service '{service.name}' mis à jour")
                return redirect('pharmacy:list_services')
                
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")
    
    service.price_major = Decimal(service.price) / 100
    
    context = {
        'service': service,
        'categories': PharmacyService.SERVICE_CATEGORY_CHOICES,
    }
    return render(request, 'pharmacy/service_edit.html', context)


@login_required
@role_required('pharmacy')
@require_http_methods(["POST"])
def delete_pharmacy_service(request, service_id):
    """Delete (deactivate) a pharmacy service"""
    pharmacy = request.user.participant
    service = get_object_or_404(PharmacyService, id=service_id, pharmacy=pharmacy)
    
    service.is_active = False
    service.is_available = False
    service.save()
    
    messages.success(request, f"Service '{service.name}' désactivé")
    return redirect('pharmacy:list_services')
