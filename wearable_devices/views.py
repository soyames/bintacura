from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Min, Max, Count
from django.db.models.functions import TruncDate
from datetime import timedelta
from django.utils import timezone
import secrets
import logging

logger = logging.getLogger(__name__)

from .models import WearableDevice, WearableData, WearableSyncLog
from .serializers import (
    WearableDeviceSerializer, WearableDataSerializer,
    WearableSyncLogSerializer, WearableDataAggregateSerializer
)
from .services import GoogleFitService


class WearableDevicesView(LoginRequiredMixin, TemplateView):
    """View to manage wearable devices"""
    template_name = 'wearable_devices/devices.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.request.user
        
        # Get unique active/connected devices per type
        devices = []
        seen_types = set()
        
        for device in WearableDevice.objects.filter(patient=patient).order_by('-created_at'):
            if device.device_type not in seen_types:
                devices.append(device)
                seen_types.add(device.device_type)
        
        context['devices'] = devices
        
        # Calculate statistics
        today = timezone.now().date()
        data_points_today = WearableData.objects.filter(
            patient=patient,
            timestamp__date=today
        ).count()
        context['data_points_today'] = data_points_today
        
        # Get last sync time from all devices
        all_devices = WearableDevice.objects.filter(patient=patient, last_sync__isnull=False).order_by('-last_sync')
        last_sync = all_devices.first()
        context['last_sync'] = last_sync.last_sync if last_sync else None
        
        context['available_device_types'] = WearableDevice.DEVICE_TYPES
        return context


class WearableDeviceViewSet(viewsets.ModelViewSet):
    """API ViewSet for wearable devices"""
    serializer_class = WearableDeviceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WearableDevice.objects.filter(patient=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Manually trigger sync for a device"""
        device = self.get_object()
        
        try:
            if device.device_type == 'google_fit':
                service = GoogleFitService(device)
                sync_log = service.sync_data()
                
                return Response({
                    'status': 'success',
                    'message': 'Sync completed successfully',
                    'records_synced': sync_log.records_stored
                })
            elif device.device_type == 'fitbit':
                from .services import FitbitService
                service = FitbitService(device)
                sync_log = service.sync_data()
                
                return Response({
                    'status': 'success',
                    'message': 'Données synchronisées avec succès',
                    'records_synced': sync_log.records_stored
                })
            else:
                return Response({
                    'status': 'error',
                    'message': f'Sync not implemented for {device.get_device_type_display()}'
                }, status=status.HTTP_501_NOT_IMPLEMENTED)
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        """Disconnect a device"""
        try:
            from communication.models import Notification
            device = self.get_object()
            device_name = device.device_name
            device_type = device.device_type
            
            # Update device status
            device.status = 'disconnected'
            device.access_token = None
            device.refresh_token = None
            device.token_expires_at = None
            device.save()
            
            # Create notification
            try:
                Notification.objects.create(
                    recipient=request.user,
                    title='Appareil Déconnecté',
                    message=f'Votre appareil {device_type.replace("_", " ").title()} "{device_name}" a été déconnecté avec succès.',
                    notification_type='info'
                )
            except Exception as notif_error:
                # If notification fails, still succeed with disconnect
                print(f"Notification error: {notif_error}")
            
            return Response({
                'status': 'success',
                'message': 'Appareil déconnecté avec succès'
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Erreur lors de la déconnexion: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get', 'put'])
    def wearable_device_settings(self, request, pk=None):
        """Get or update wearable device settings"""
        device = self.get_object()
        
        if request.method == 'GET':
            return Response({
                'auto_sync': device.auto_sync,
                'sync_frequency': device.sync_frequency,
                'device_name': device.device_name
            })
        elif request.method == 'PUT':
            # Update settings
            if 'auto_sync' in request.data:
                device.auto_sync = request.data['auto_sync']
            if 'sync_frequency' in request.data:
                device.sync_frequency = request.data['sync_frequency']
            if 'device_name' in request.data:
                device.device_name = request.data['device_name']
            
            device.save()
            
            return Response({
                'status': 'success',
                'message': 'Paramètres mis à jour avec succès',
                'settings': {
                    'auto_sync': device.auto_sync,
                    'sync_frequency': device.sync_frequency,
                    'device_name': device.device_name
                }
            })
    
    @action(detail=False, methods=['get'])
    def connect_google_fit(self, request):
        """Initiate Google Fit OAuth flow"""
        # Generate state token for CSRF protection
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        request.session['oauth_device_type'] = 'google_fit'
        
        # Create temporary device record
        device = WearableDevice.objects.create(
            patient=request.user,
            device_type='google_fit',
            device_name='Google Fit',
            status='disconnected'
        )
        request.session['oauth_device_id'] = str(device.id)
        
        service = GoogleFitService(device)
        redirect_uri = request.build_absolute_uri('/patient/wearable-devices/oauth/callback/')
        auth_url = service.get_authorization_url(redirect_uri, state)
        
        return Response({
            'authorization_url': auth_url
        })


@login_required
def oauth_callback(request):
    """Handle OAuth callback"""
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    
    # Verify state
    if state != request.session.get('oauth_state'):
        messages.error(request, 'État OAuth invalide. Veuillez réessayer.')
        return redirect('/patient/wearable-devices/')
    
    if error:
        messages.error(request, f'Échec de l\'autorisation : {error}')
        return redirect('/patient/wearable-devices/')
    
    try:
        device_id = request.session.get('oauth_device_id')
        device_type = request.session.get('oauth_device_type')
        device = WearableDevice.objects.get(id=device_id, patient=request.user)
        
        if device_type == 'google_fit':
            from communication.models import Notification
            service = GoogleFitService(device)
            redirect_uri = request.build_absolute_uri('/patient/wearable-devices/oauth/callback/')
            service.exchange_code_for_token(code, redirect_uri)
            
            # Update device status to connected
            device.status = 'active'
            device.last_sync = timezone.now()
            device.save(update_fields=['status', 'last_sync'])
            
            # Trigger initial sync
            try:
                service.sync_data()
                messages.success(request, 'Google Fit connecté avec succès et données synchronisées !')
                
                # Create notification
                Notification.objects.create(
                    recipient=request.user,
                    title='Google Fit Connecté',
                    message=f'Votre compte Google Fit a été connecté et synchronisé avec succès.',
                    notification_type='success'
                )
            except Exception as sync_error:
                # Log error for developers but show user-friendly message
                logger.error(f'Initial Google Fit sync failed for device {device.id}: {str(sync_error)}')
                messages.success(request, 'Votre compte Google Fit a été connecté avec succès. La synchronisation des données commencera sous peu.')
                
                # Create notification with positive message
                Notification.objects.create(
                    recipient=request.user,
                    title='Google Fit Connecté',
                    message='Votre compte Google Fit a été connecté avec succès. La synchronisation des données commencera sous peu.',
                    notification_type='success'
                )
        
        elif device_type == 'fitbit':
            from .services import FitbitService
            from communication.models import Notification
            
            # Get PKCE verifier from session
            code_verifier = request.session.get('pkce_verifier')
            if not code_verifier:
                raise ValueError("PKCE verifier not found in session")
            
            service = FitbitService(device)
            redirect_uri = request.build_absolute_uri('/patient/wearable-devices/oauth/callback/')
            service.exchange_code_for_token(code, redirect_uri, code_verifier)
            
            # Update device status to connected
            device.status = 'active'
            device.last_sync = timezone.now()
            device.save(update_fields=['status', 'last_sync'])
            
            # Trigger initial sync
            try:
                service.sync_data()
                messages.success(request, 'Fitbit connecté avec succès et données synchronisées !')
                
                # Create notification
                Notification.objects.create(
                    recipient=request.user,
                    title='Fitbit Connecté',
                    message=f'Votre appareil Fitbit "{device.device_name}" a été connecté et synchronisé avec succès.',
                    notification_type='success'
                )
            except Exception as sync_error:
                # Log error for developers but show user-friendly message  
                logger.error(f'Initial Fitbit sync failed for device {device.id}: {str(sync_error)}')
                messages.success(request, 'Votre appareil Fitbit a été connecté avec succès. La synchronisation des données commencera sous peu.')
                
                # Create notification with positive message
                Notification.objects.create(
                    recipient=request.user,
                    title='Fitbit Connecté',
                    message=f'Votre appareil Fitbit "{device.device_name}" a été connecté avec succès. La synchronisation des données commencera sous peu.',
                    notification_type='success'
                )
        
        # Clean up session
        if 'oauth_state' in request.session:
            del request.session['oauth_state']
        if 'oauth_device_type' in request.session:
            del request.session['oauth_device_type']
        if 'oauth_device_id' in request.session:
            del request.session['oauth_device_id']
        if 'pkce_verifier' in request.session:
            del request.session['pkce_verifier']
        
    except Exception as e:
        messages.error(request, f'Échec de l\'autorisation : {str(e)}')
    
    return redirect('/patient/wearable-devices/')


@login_required
def connect_device(request, device_type):
    """Initiate device connection flow - max 2 devices allowed"""
    # Check if this device type is already connected
    existing_active_device = WearableDevice.objects.filter(
        patient=request.user,
        device_type=device_type,
        status='active'
    ).first()
    
    if existing_active_device:
        messages.info(request, f'{device_type.replace("_", " ").title()} est déjà connecté.')
        return redirect('/patient/wearable-devices/')
    
    # Check active device count (max 2 total)
    active_devices_count = WearableDevice.objects.filter(
        patient=request.user,
        status='active'
    ).exclude(device_type=device_type).count()
    
    if active_devices_count >= 2:
        messages.error(request, 'Vous avez atteint la limite de 2 appareils connectés. Déconnectez un appareil avant d\'en ajouter un nouveau.')
        return redirect('/patient/wearable-devices/')
    
    # Get or create device (reuse existing device of same type)
    device, created = WearableDevice.objects.get_or_create(
        patient=request.user,
        device_type=device_type,
        defaults={
            'device_name': device_type.replace('_', ' ').title(),
            'status': 'pending',
        }
    )
    
    if not created:
        # Clear old credentials for reconnection
        device.access_token = None
        device.refresh_token = None
        device.token_expires_at = None
        device.status = 'pending'
        device.save()
    
    # Generate state parameter
    import secrets
    state = secrets.token_urlsafe(32)
    
    # Store state and device info in session
    request.session['oauth_state'] = state
    request.session['oauth_device_type'] = device_type
    request.session['oauth_device_id'] = str(device.id)
    
    redirect_uri = request.build_absolute_uri('/patient/wearable-devices/oauth/callback/')
    
    if device_type == 'fitbit':
        from .services import FitbitService
        
        # Generate PKCE pair
        code_verifier, code_challenge = FitbitService.generate_pkce_pair()
        
        # Store code verifier in session
        request.session['pkce_verifier'] = code_verifier
        
        service = FitbitService(device)
        auth_url = service.get_authorization_url(redirect_uri, state, code_challenge)
        return redirect(auth_url)
    
    elif device_type == 'google_fit':
        from .services import GoogleFitService
        service = GoogleFitService(device)
        auth_url = service.get_authorization_url(redirect_uri, state)
        return redirect(auth_url)
    
    messages.error(request, 'Type d\'appareil non supporté.')
    return redirect('/patient/wearable-devices/')
    if active_devices >= 2:
        messages.warning(request, 'Vous avez atteint la limite de 2 appareils connectés. Veuillez en déconnecter un pour en ajouter un nouveau.')
        return redirect('/patient/wearable-devices/')
    
    if device_type == 'google_fit':
        messages.info(request, 'Intégration Google Fit bientôt disponible ! Nous configurons les identifiants OAuth de Google Cloud Platform.')
        return redirect('/patient/wearable-devices/')
    
    elif device_type == 'fitbit':
        from .services import FitbitService
        
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        request.session['oauth_device_type'] = device_type
        
        # Get or create device (only one per type per patient)
        device, created = WearableDevice.objects.get_or_create(
            patient=request.user,
            device_type='fitbit',
            defaults={
                'device_name': 'Fitbit',
                'status': 'pending'
            }
        )
        
        # If reconnecting, clear old credentials and mark as pending
        if not created:
            device.access_token = None
            device.refresh_token = None
            device.token_expires_at = None
            device.status = 'pending'  # Mark as pending during OAuth
            device.save()
        
        request.session['oauth_device_id'] = str(device.id)
        
        service = FitbitService(device)
        redirect_uri = request.build_absolute_uri('/patient/wearable-devices/oauth/callback/')
        auth_url = service.get_authorization_url(redirect_uri, state)
        
        return redirect(auth_url)
    
    else:
        messages.error(request, f'Type d\'appareil inconnu : {device_type}')
        return redirect('/patient/wearable-devices/')


class WearableDataViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet for wearable data"""
    serializer_class = WearableDataSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = WearableData.objects.filter(patient=self.request.user)
        
        # Filter by data type
        data_type = self.request.query_params.get('data_type')
        if data_type:
            queryset = queryset.filter(data_type=data_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        # Filter by device
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        
        return queryset.order_by('-timestamp')
    
    @action(detail=False, methods=['get'])
    def aggregate(self, request):
        """Get aggregated wearable data"""
        data_type = request.query_params.get('data_type')
        days = int(request.query_params.get('days', 7))
        
        start_date = timezone.now() - timedelta(days=days)
        
        queryset = WearableData.objects.filter(
            patient=request.user,
            timestamp__gte=start_date
        )
        
        if data_type:
            queryset = queryset.filter(data_type=data_type)
        
        # Aggregate by date
        aggregated = queryset.annotate(
            date=TruncDate('timestamp')
        ).values('data_type', 'date').annotate(
            avg_value=Avg('value'),
            min_value=Min('value'),
            max_value=Max('value'),
            count=Count('id')
        ).values('data_type', 'date', 'avg_value', 'min_value', 'max_value', 'count', 'unit')
        
        serializer = WearableDataAggregateSerializer(aggregated, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest values for each data type"""
        latest_data = {}
        
        for data_type, _ in WearableData.DATA_TYPES:
            latest = WearableData.objects.filter(
                patient=request.user,
                data_type=data_type
            ).order_by('-timestamp').first()
            
            if latest:
                latest_data[data_type] = {
                    'value': latest.value,
                    'unit': latest.unit,
                    'timestamp': latest.timestamp,
                    'device': latest.device.device_name
                }
        
        return Response(latest_data)


class WearableSyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet for sync logs"""
    serializer_class = WearableSyncLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        device_id = self.request.query_params.get('device_id')
        queryset = WearableSyncLog.objects.filter(device__patient=self.request.user)
        
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        
        return queryset.order_by('-sync_started_at')[:50]  # Last 50 syncs


@login_required
def wearable_settings(request, device_id):
    """Get or update wearable device settings"""
    from django.http import JsonResponse
    import json
    
    try:
        device = WearableDevice.objects.get(id=device_id, patient=request.user)
    except WearableDevice.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Appareil non trouvé'}, status=404)
    
    if request.method == 'GET':
        # Return current settings
        return JsonResponse({
            'auto_sync_enabled': device.auto_sync_enabled,
            'sync_frequency': device.sync_frequency,
            'sync_heart_rate': device.sync_settings.get('sync_heart_rate', True),
            'sync_steps': device.sync_settings.get('sync_steps', True),
            'sync_sleep': device.sync_settings.get('sync_sleep', True),
            'sync_activity': device.sync_settings.get('sync_activity', True),
            'sync_calories': device.sync_settings.get('sync_calories', True),
        })
    
    elif request.method == 'POST':
        # Update settings
        try:
            data = json.loads(request.body)
            
            device.auto_sync_enabled = data.get('auto_sync_enabled', device.auto_sync_enabled)
            device.sync_frequency = data.get('sync_frequency', device.sync_frequency)
            
            # Update sync settings
            if not device.sync_settings:
                device.sync_settings = {}
            
            device.sync_settings['sync_heart_rate'] = data.get('sync_heart_rate', True)
            device.sync_settings['sync_steps'] = data.get('sync_steps', True)
            device.sync_settings['sync_sleep'] = data.get('sync_sleep', True)
            device.sync_settings['sync_activity'] = data.get('sync_activity', True)
            device.sync_settings['sync_calories'] = data.get('sync_calories', True)
            
            device.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Paramètres enregistrés avec succès'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
