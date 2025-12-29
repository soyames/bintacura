from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Advertisement


@require_POST
@csrf_exempt
def track_ad_view(request, ad_id):
    """Track when an ad is viewed"""
    try:
        ad = get_object_or_404(Advertisement, id=ad_id, status='active')
        ad.increment_views()
        return JsonResponse({'success': True, 'views': ad.view_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
@csrf_exempt
def track_ad_click(request, ad_id):
    """Track when an ad button is clicked"""
    try:
        ad = get_object_or_404(Advertisement, id=ad_id, status='active')
        ad.increment_clicks()
        return JsonResponse({'success': True, 'clicks': ad.click_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
