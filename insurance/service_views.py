"""
Insurance Service Management Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_http_methods
from decimal import Decimal

from core.models import Participant
from insurance.service_models import InsuranceService
from core.regional_service_helper import RegionalServiceHelper
from core.decorators import role_required


@login_required
@role_required('insurance_company')
@require_http_methods(["GET", "POST"])
def create_insurance_service(request):
    """Create a new insurance service/plan with regional pricing"""
    
    insurance_company = request.user.participant
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                name = request.POST.get('name', '').strip()
                category = request.POST.get('category', '')
                description = request.POST.get('description', '').strip()
                premium_str = request.POST.get('premium_amount', '0')
                coverage_str = request.POST.get('coverage_limit', '')
                payment_frequency = request.POST.get('payment_frequency', 'monthly')
                min_age = request.POST.get('minimum_age', '')
                max_age = request.POST.get('maximum_age', '')
                waiting_period = request.POST.get('waiting_period_days', '0')
                
                if not name or not category:
                    messages.error(request, "Le nom et la catégorie sont requis")
                    return redirect('insurance:create_service')
                
                # Parse premium
                try:
                    premium_major = Decimal(premium_str)
                    premium_cents = int(premium_major * 100)
                except:
                    messages.error(request, "Montant de la prime invalide")
                    return redirect('insurance:create_service')
                
                # Parse coverage limit if provided
                coverage_cents = None
                if coverage_str:
                    try:
                        coverage_major = Decimal(coverage_str)
                        coverage_cents = int(coverage_major * 100)
                    except:
                        pass
                
                is_valid, error_msg = RegionalServiceHelper.validate_service_price(
                    premium_cents, 'insurance'
                )
                if not is_valid:
                    messages.error(request, error_msg)
                    return redirect('insurance:create_service')
                
                region_code = RegionalServiceHelper.get_participant_region(insurance_company)
                currency = RegionalServiceHelper.get_participant_currency(insurance_company)
                
                service = InsuranceService.objects.create(
                    region_code=region_code,
                    insurance_company=insurance_company,
                    name=name,
                    category=category,
                    description=description,
                    premium_amount=premium_cents,
                    currency=currency,
                    payment_frequency=payment_frequency,
                    coverage_limit=coverage_cents,
                    minimum_age=int(min_age) if min_age else None,
                    maximum_age=int(max_age) if max_age else None,
                    waiting_period_days=int(waiting_period) if waiting_period else 0,
                    is_available=True,
                    is_active=True
                )
                
                messages.success(
                    request,
                    f"Service '{name}' créé avec succès. Prime: {RegionalServiceHelper.format_price_display(premium_cents, currency)}"
                )
                return redirect('insurance:list_services')
                
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")
            return redirect('insurance:create_service')
    
    context = {
        'categories': InsuranceService.SERVICE_CATEGORY_CHOICES,
        'payment_frequencies': [
            ('monthly', 'Mensuel'),
            ('quarterly', 'Trimestriel'),
            ('semi_annual', 'Semestriel'),
            ('annual', 'Annuel'),
        ],
        'default_currency': RegionalServiceHelper.get_participant_currency(insurance_company),
        'region_code': RegionalServiceHelper.get_participant_region(insurance_company),
    }
    return render(request, 'insurance/service_create.html', context)


@login_required
@role_required('insurance_company')
def list_insurance_services(request):
    """List all services for this insurance company"""
    insurance_company = request.user.participant
    services = InsuranceService.objects.filter(
        insurance_company=insurance_company
    ).order_by('-created_at')
    
    for service in services:
        service.premium_display = RegionalServiceHelper.format_price_display(
            service.premium_amount, service.currency
        )
        if service.coverage_limit:
            service.coverage_display = RegionalServiceHelper.format_price_display(
                service.coverage_limit, service.currency
            )
    
    context = {'services': services}
    return render(request, 'insurance/service_list.html', context)


@login_required
@role_required('insurance_company')
@require_http_methods(["GET", "POST"])
def edit_insurance_service(request, service_id):
    """Edit an existing insurance service"""
    insurance_company = request.user.participant
    service = get_object_or_404(
        InsuranceService, id=service_id, insurance_company=insurance_company
    )
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                service.name = request.POST.get('name', service.name).strip()
                service.category = request.POST.get('category', service.category)
                service.description = request.POST.get('description', '').strip()
                service.payment_frequency = request.POST.get('payment_frequency', service.payment_frequency)
                
                # Update premium
                premium_str = request.POST.get('premium_amount', '0')
                try:
                    premium_major = Decimal(premium_str)
                    service.premium_amount = int(premium_major * 100)
                except:
                    messages.error(request, "Montant de la prime invalide")
                    return redirect('insurance:edit_service', service_id=service_id)
                
                # Update coverage limit
                coverage_str = request.POST.get('coverage_limit', '')
                if coverage_str:
                    try:
                        coverage_major = Decimal(coverage_str)
                        service.coverage_limit = int(coverage_major * 100)
                    except:
                        service.coverage_limit = None
                
                min_age = request.POST.get('minimum_age', '')
                service.minimum_age = int(min_age) if min_age else None
                
                max_age = request.POST.get('maximum_age', '')
                service.maximum_age = int(max_age) if max_age else None
                
                waiting = request.POST.get('waiting_period_days', '0')
                service.waiting_period_days = int(waiting) if waiting else 0
                
                service.is_available = request.POST.get('is_available') == 'on'
                
                service.save()
                
                messages.success(request, f"Service '{service.name}' mis à jour")
                return redirect('insurance:list_services')
                
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")
    
    service.premium_major = Decimal(service.premium_amount) / 100
    if service.coverage_limit:
        service.coverage_major = Decimal(service.coverage_limit) / 100
    
    context = {
        'service': service,
        'categories': InsuranceService.SERVICE_CATEGORY_CHOICES,
        'payment_frequencies': [
            ('monthly', 'Mensuel'),
            ('quarterly', 'Trimestriel'),
            ('semi_annual', 'Semestriel'),
            ('annual', 'Annuel'),
        ],
    }
    return render(request, 'insurance/service_edit.html', context)


@login_required
@role_required('insurance_company')
@require_http_methods(["POST"])
def delete_insurance_service(request, service_id):
    """Delete (deactivate) an insurance service"""
    insurance_company = request.user.participant
    service = get_object_or_404(
        InsuranceService, id=service_id, insurance_company=insurance_company
    )
    
    service.is_active = False
    service.is_available = False
    service.save()
    
    messages.success(request, f"Service '{service.name}' désactivé")
    return redirect('insurance:list_services')
