import requests
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from zoneinfo import ZoneInfo
from .models import WearableDevice, WearableData, WearableSyncLog

logger = logging.getLogger(__name__)


class GoogleFitService:
    """Service to interact with Google Fit API"""
    
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE_URL = "https://www.googleapis.com/fitness/v1/users/me"
    
    SCOPES = [
        "https://www.googleapis.com/auth/fitness.activity.read",
        "https://www.googleapis.com/auth/fitness.body.read",
        "https://www.googleapis.com/auth/fitness.heart_rate.read",
        "https://www.googleapis.com/auth/fitness.sleep.read",
        "https://www.googleapis.com/auth/fitness.blood_pressure.read",
        "https://www.googleapis.com/auth/fitness.blood_glucose.read",
        "https://www.googleapis.com/auth/fitness.body_temperature.read",
        "https://www.googleapis.com/auth/fitness.oxygen_saturation.read",
    ]
    
    def __init__(self, device):
        self.device = device
    
    def get_authorization_url(self, redirect_uri, state):
        """
        Generate OAuth authorization URL
        
        Note: If the user doesn't have a Google account, Google's OAuth flow
        will redirect them to create one during the authorization process.
        """
        params = {
            'client_id': settings.GOOGLE_FIT_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.SCOPES),
            'access_type': 'offline',
            'state': state,
            'prompt': 'consent',
        }
        return f"{self.AUTH_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    def exchange_code_for_token(self, code, redirect_uri):
        """Exchange authorization code for access token"""
        data = {
            'client_id': settings.GOOGLE_FIT_CLIENT_ID,
            'client_secret': settings.GOOGLE_FIT_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Store tokens
        self.device.access_token = token_data['access_token']
        if 'refresh_token' in token_data:
            self.device.refresh_token = token_data['refresh_token']
        
        # Calculate expiry
        expires_in = token_data.get('expires_in', 3600)
        self.device.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
        self.device.status = 'active'
        self.device.save()
        
        return token_data
    
    def refresh_access_token(self):
        """Refresh the access token"""
        if not self.device.refresh_token:
            raise ValueError("No refresh token available")
        
        data = {
            'client_id': settings.GOOGLE_FIT_CLIENT_ID,
            'client_secret': settings.GOOGLE_FIT_CLIENT_SECRET,
            'refresh_token': self.device.refresh_token,
            'grant_type': 'refresh_token',
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.device.access_token = token_data['access_token']
        
        expires_in = token_data.get('expires_in', 3600)
        self.device.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
        self.device.save()
        
        return token_data
    
    def _get_headers(self):
        """Get authorization headers"""
        # Check if token needs refresh
        if self.device.token_expires_at and self.device.token_expires_at <= timezone.now():
            self.refresh_access_token()
        
        return {
            'Authorization': f'Bearer {self.device.access_token}',
            'Content-Type': 'application/json',
        }
    
    def sync_data(self, start_date=None, end_date=None):
        """Sync data from Google Fit"""
        if not start_date:
            start_date = self.device.last_sync or (timezone.now() - timedelta(days=7))
        if not end_date:
            end_date = timezone.now()
        
        sync_log = WearableSyncLog.objects.create(
            device=self.device,
            status='failed'
        )
        
        try:
            total_records = 0
            
            # Sync different data types
            if self.device.data_types_enabled.get('steps', True):
                total_records += self._sync_steps(start_date, end_date)
            
            if self.device.data_types_enabled.get('heart_rate', True):
                total_records += self._sync_heart_rate(start_date, end_date)
            
            if self.device.data_types_enabled.get('sleep', True):
                total_records += self._sync_sleep(start_date, end_date)
            
            if self.device.data_types_enabled.get('calories', True):
                total_records += self._sync_calories(start_date, end_date)
            
            # Update sync log
            sync_log.status = 'success'
            sync_log.records_fetched = total_records
            sync_log.records_stored = total_records
            sync_log.sync_completed_at = timezone.now()
            sync_log.save()
            
            # Update device last sync
            self.device.last_sync = timezone.now()
            self.device.save()
            
            return sync_log
            
        except Exception as e:
            sync_log.status = 'failed'
            sync_log.errors.append(str(e))
            sync_log.sync_completed_at = timezone.now()
            sync_log.save()
            raise
    
    def _sync_steps(self, start_date, end_date):
        """Sync step count data"""
        data_type_name = "com.google.step_count.delta"
        return self._fetch_aggregate_data('steps', data_type_name, start_date, end_date, 'count')
    
    def _sync_heart_rate(self, start_date, end_date):
        """Sync heart rate data"""
        data_type_name = "com.google.heart_rate.bpm"
        return self._fetch_aggregate_data('heart_rate', data_type_name, start_date, end_date, 'bpm')
    
    def _sync_sleep(self, start_date, end_date):
        """Sync sleep data"""
        data_type_name = "com.google.sleep.segment"
        return self._fetch_aggregate_data('sleep', data_type_name, start_date, end_date, 'minutes')
    
    def _sync_calories(self, start_date, end_date):
        """Sync calories burned data"""
        data_type_name = "com.google.calories.expended"
        return self._fetch_aggregate_data('calories', data_type_name, start_date, end_date, 'kcal')
    
    def _fetch_aggregate_data(self, data_type, data_type_name, start_date, end_date, unit):
        """Fetch aggregate data from Google Fit"""
        url = f"{self.API_BASE_URL}/dataset:aggregate"
        
        # Ensure times are in UTC
        if timezone.is_naive(start_date):
            start_date = timezone.make_aware(start_date, ZoneInfo('UTC'))
        if timezone.is_naive(end_date):
            end_date = timezone.make_aware(end_date, ZoneInfo('UTC'))
        
        # Build the request body without dataSourceId
        body = {
            "aggregateBy": [{
                "dataTypeName": data_type_name
            }],
            "bucketByTime": {"durationMillis": 86400000},  # 1 day
            "startTimeMillis": int(start_date.timestamp() * 1000),
            "endTimeMillis": int(end_date.timestamp() * 1000),
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=body)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(f"Google Fit API error for {data_type}: {e.response.text if e.response else str(e)}")
            raise
        
        data = response.json()
        records_created = 0
        
        for bucket in data.get('bucket', []):
            timestamp = datetime.fromtimestamp(int(bucket['startTimeMillis']) / 1000, tz=ZoneInfo('UTC'))
            
            for dataset in bucket.get('dataset', []):
                for point in dataset.get('point', []):
                    for value in point.get('value', []):
                        value_num = value.get('intVal') or value.get('fpVal')
                        if value_num is not None:
                            WearableData.objects.update_or_create(
                                device=self.device,
                                patient=self.device.patient,
                                data_type=data_type,
                                timestamp=timestamp,
                                source_id=point.get('originDataSourceId', ''),
                                defaults={
                                    'value': float(value_num),
                                    'unit': unit,
                                    'metadata': {
                                        'dataSourceId': dataset.get('dataSourceId'),
                                        'originDataSourceId': point.get('originDataSourceId'),
                                    }
                                }
                            )
                            records_created += 1
        
        return records_created


class FitbitService:
    """Service to interact with Fitbit API"""
    
    AUTH_URL = "https://www.fitbit.com/oauth2/authorize"
    TOKEN_URL = "https://api.fitbit.com/oauth2/token"
    API_BASE_URL = "https://api.fitbit.com/1/user/-"
    
    SCOPES = [
        "activity",
        "heartrate",
        "sleep",
        "weight",
        "profile",
        "nutrition",
        "oxygen_saturation",
        "respiratory_rate",
        "temperature",
        "cardio_fitness",
    ]
    
    def __init__(self, device):
        self.device = device
    
    @staticmethod
    def generate_pkce_pair():
        """Generate PKCE code verifier and challenge"""
        import secrets
        import hashlib
        import base64
        
        # Generate code verifier (43-128 chars)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Generate code challenge (SHA256 hash of verifier)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_authorization_url(self, redirect_uri, state, code_challenge):
        """
        Generate OAuth authorization URL with PKCE
        
        Note: If the user doesn't have a Fitbit account, Fitbit's OAuth flow
        will automatically redirect them to create one during the authorization process.
        """
        from urllib.parse import urlencode, quote
        
        params = {
            'client_id': settings.FITBIT_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.SCOPES),
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }
        return f"{self.AUTH_URL}?{urlencode(params, quote_via=quote)}"
    
    def exchange_code_for_token(self, code, redirect_uri, code_verifier):
        """Exchange authorization code for access token with PKCE"""
        from base64 import b64encode
        
        # Fitbit requires Basic Auth with client_id:client_secret
        auth_string = f"{settings.FITBIT_CLIENT_ID}:{settings.FITBIT_CLIENT_SECRET}"
        auth_header = b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        data = {
            'client_id': settings.FITBIT_CLIENT_ID,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
            'code_verifier': code_verifier,
        }
        
        response = requests.post(self.TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Save tokens
        self.device.access_token = token_data['access_token']
        self.device.refresh_token = token_data['refresh_token']
        expires_in = token_data.get('expires_in', 28800)  # Fitbit tokens last 8 hours
        self.device.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
        self.device.device_id = token_data['user_id']
        self.device.status = 'active'
        self.device.save()
        
        return token_data
    
    def refresh_access_token(self):
        """Refresh the access token"""
        if not self.device.refresh_token:
            raise ValueError("No refresh token available")
        
        from base64 import b64encode
        
        auth_string = f"{settings.FITBIT_CLIENT_ID}:{settings.FITBIT_CLIENT_SECRET}"
        auth_header = b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.device.refresh_token,
        }
        
        response = requests.post(self.TOKEN_URL, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.device.access_token = token_data['access_token']
        self.device.refresh_token = token_data['refresh_token']
        expires_in = token_data.get('expires_in', 28800)
        self.device.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
        self.device.save()
        
        return token_data
    
    def _get_headers(self):
        """Get authorization headers"""
        # Check if token needs refresh
        if self.device.token_expires_at and self.device.token_expires_at <= timezone.now():
            self.refresh_access_token()
        
        return {
            'Authorization': f'Bearer {self.device.access_token}',
        }
    
    def sync_data(self, start_date=None, end_date=None):
        """Sync data from Fitbit"""
        if not start_date:
            start_date = self.device.last_sync or (timezone.now() - timedelta(days=7))
        if not end_date:
            end_date = timezone.now()
        
        sync_log = WearableSyncLog.objects.create(
            device=self.device,
            status='failed'
        )
        
        try:
            total_records = 0
            
            # Sync different data types based on enabled settings
            if self.device.data_types_enabled.get('steps', True):
                total_records += self._sync_activities(start_date, end_date)
            
            if self.device.data_types_enabled.get('heart_rate', True):
                total_records += self._sync_heart_rate(start_date, end_date)
            
            if self.device.data_types_enabled.get('sleep', True):
                total_records += self._sync_sleep(start_date, end_date)
            
            if self.device.data_types_enabled.get('blood_oxygen', True):
                total_records += self._sync_spo2(start_date, end_date)
            
            if self.device.data_types_enabled.get('body_temperature', True):
                total_records += self._sync_temperature(start_date, end_date)
            
            if self.device.data_types_enabled.get('respiratory_rate', True):
                total_records += self._sync_breathing_rate(start_date, end_date)
            
            if self.device.data_types_enabled.get('hrv', True):
                total_records += self._sync_hrv(start_date, end_date)
            
            if self.device.data_types_enabled.get('vo2_max', True):
                total_records += self._sync_cardio_fitness(start_date, end_date)
            
            if self.device.data_types_enabled.get('weight', True):
                total_records += self._sync_body_composition(start_date, end_date)
            
            # Update sync log
            sync_log.status = 'success'
            sync_log.records_fetched = total_records
            sync_log.records_stored = total_records
            sync_log.sync_completed_at = timezone.now()
            sync_log.save()
            
            # Update device last sync
            self.device.last_sync = timezone.now()
            self.device.save()
            
            return sync_log
            
        except Exception as e:
            sync_log.status = 'failed'
            sync_log.errors.append(str(e))
            sync_log.sync_completed_at = timezone.now()
            sync_log.save()
            raise
    
    def _sync_activities(self, start_date, end_date):
        """Sync activity data (steps, distance, calories)"""
        records_created = 0
        current_date = start_date.date()
        end = end_date.date()
        
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            url = f"{self.API_BASE_URL}/activities/date/{date_str}.json"
            
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            summary = data.get('summary', {})
            timestamp = datetime.combine(current_date, datetime.min.time()).replace(tzinfo=ZoneInfo('UTC'))
            
            # Steps
            if 'steps' in summary:
                WearableData.objects.update_or_create(
                    device=self.device,
                    patient=self.device.patient,
                    data_type='steps',
                    timestamp=timestamp,
                    defaults={
                        'value': summary['steps'],
                        'unit': 'count',
                        'metadata': {'date': date_str}
                    }
                )
                records_created += 1
            
            # Distance
            if 'distances' in summary and summary['distances']:
                total_distance = sum(d.get('distance', 0) for d in summary['distances'])
                WearableData.objects.update_or_create(
                    device=self.device,
                    patient=self.device.patient,
                    data_type='distance',
                    timestamp=timestamp,
                    defaults={
                        'value': total_distance,
                        'unit': 'km',
                        'metadata': {'date': date_str}
                    }
                )
                records_created += 1
            
            # Calories
            if 'caloriesOut' in summary:
                WearableData.objects.update_or_create(
                    device=self.device,
                    patient=self.device.patient,
                    data_type='calories',
                    timestamp=timestamp,
                    defaults={
                        'value': summary['caloriesOut'],
                        'unit': 'kcal',
                        'metadata': {'date': date_str}
                    }
                )
                records_created += 1
            
            current_date += timedelta(days=1)
        
        return records_created
    
    def _sync_heart_rate(self, start_date, end_date):
        """Sync heart rate data"""
        records_created = 0
        current_date = start_date.date()
        end = end_date.date()
        
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            url = f"{self.API_BASE_URL}/activities/heart/date/{date_str}/1d.json"
            
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            
            if 'activities-heart' in data and data['activities-heart']:
                heart_data = data['activities-heart'][0]
                value_data = heart_data.get('value', {})
                
                if 'restingHeartRate' in value_data:
                    timestamp = datetime.combine(current_date, datetime.min.time()).replace(tzinfo=ZoneInfo('UTC'))
                    WearableData.objects.update_or_create(
                        device=self.device,
                        patient=self.device.patient,
                        data_type='heart_rate',
                        timestamp=timestamp,
                        defaults={
                            'value': value_data['restingHeartRate'],
                            'unit': 'bpm',
                            'metadata': {
                                'date': date_str,
                                'type': 'resting',
                                'heartRateZones': value_data.get('heartRateZones', [])
                            }
                        }
                    )
                    records_created += 1
            
            current_date += timedelta(days=1)
        
        return records_created
    
    def _sync_sleep(self, start_date, end_date):
        """Sync sleep data"""
        records_created = 0
        current_date = start_date.date()
        end = end_date.date()
        
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            url = f"{self.API_BASE_URL}/sleep/date/{date_str}.json"
            
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            
            if 'sleep' in data and data['sleep']:
                for sleep_record in data['sleep']:
                    timestamp_str = sleep_record.get('startTime')
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        
                        WearableData.objects.update_or_create(
                            device=self.device,
                            patient=self.device.patient,
                            data_type='sleep',
                            timestamp=timestamp,
                            source_id=str(sleep_record.get('logId')),
                            defaults={
                                'value': sleep_record.get('duration', 0) / 60000,  # Convert to minutes
                                'unit': 'minutes',
                                'metadata': {
                                    'efficiency': sleep_record.get('efficiency'),
                                    'minutesAsleep': sleep_record.get('minutesAsleep'),
                                    'minutesAwake': sleep_record.get('minutesAwake'),
                                    'mainSleep': sleep_record.get('isMainSleep'),
                                }
                            }
                        )
                        records_created += 1
            
            current_date += timedelta(days=1)
        
        return records_created
    
    def _sync_spo2(self, start_date, end_date):
        """Sync SpO2 (Blood Oxygen Saturation) data"""
        records_created = 0
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        url = f"{self.API_BASE_URL}/spo2/date/{start_str}/{end_str}.json"
        
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            
            for reading in data:
                date_str = reading.get('dateTime')
                if date_str:
                    timestamp = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=ZoneInfo('UTC'))
                    value_data = reading.get('value', {})
                    
                    if 'avg' in value_data:
                        WearableData.objects.update_or_create(
                            device=self.device,
                            patient=self.device.patient,
                            data_type='blood_oxygen',
                            timestamp=timestamp,
                            defaults={
                                'value': value_data['avg'],
                                'unit': '%',
                                'metadata': {
                                    'min': value_data.get('min'),
                                    'max': value_data.get('max'),
                                }
                            }
                        )
                        records_created += 1
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                pass
            else:
                raise
        
        return records_created
    
    def _sync_temperature(self, start_date, end_date):
        """Sync skin temperature data"""
        records_created = 0
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        url = f"{self.API_BASE_URL}/temp/skin/date/{start_str}/{end_str}.json"
        
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            
            for reading in data.get('tempSkin', []):
                date_str = reading.get('dateTime')
                if date_str:
                    timestamp = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=ZoneInfo('UTC'))
                    value_data = reading.get('value', {})
                    
                    if 'nightlyRelative' in value_data:
                        WearableData.objects.update_or_create(
                            device=self.device,
                            patient=self.device.patient,
                            data_type='body_temperature',
                            timestamp=timestamp,
                            defaults={
                                'value': value_data['nightlyRelative'],
                                'unit': '°C',
                                'metadata': {
                                    'type': 'skin',
                                    'logType': value_data.get('logType'),
                                }
                            }
                        )
                        records_created += 1
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                pass
            else:
                raise
        
        return records_created
    
    def _sync_breathing_rate(self, start_date, end_date):
        """Sync breathing rate data"""
        records_created = 0
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        url = f"{self.API_BASE_URL}/br/date/{start_str}/{end_str}.json"
        
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            
            for reading in data.get('br', []):
                date_str = reading.get('dateTime')
                if date_str:
                    timestamp = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=ZoneInfo('UTC'))
                    value_data = reading.get('value', {})
                    
                    if 'breathingRate' in value_data:
                        WearableData.objects.update_or_create(
                            device=self.device,
                            patient=self.device.patient,
                            data_type='respiratory_rate',
                            timestamp=timestamp,
                            defaults={
                                'value': value_data['breathingRate'],
                                'unit': 'breaths/min',
                                'metadata': {}
                            }
                        )
                        records_created += 1
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                pass
            else:
                raise
        
        return records_created
    
    def _sync_hrv(self, start_date, end_date):
        """Sync Heart Rate Variability data"""
        records_created = 0
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        url = f"{self.API_BASE_URL}/hrv/date/{start_str}/{end_str}.json"
        
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            
            for reading in data.get('hrv', []):
                date_str = reading.get('dateTime')
                if date_str:
                    timestamp = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=ZoneInfo('UTC'))
                    value_data = reading.get('value', {})
                    
                    if 'dailyRmssd' in value_data:
                        WearableData.objects.update_or_create(
                            device=self.device,
                            patient=self.device.patient,
                            data_type='hrv',
                            timestamp=timestamp,
                            defaults={
                                'value': value_data['dailyRmssd'],
                                'unit': 'ms',
                                'metadata': {
                                    'deepRmssd': value_data.get('deepRmssd'),
                                }
                            }
                        )
                        records_created += 1
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                pass
            else:
                raise
        
        return records_created
    
    def _sync_cardio_fitness(self, start_date, end_date):
        """Sync Cardio Fitness Score (VO2 Max) data"""
        records_created = 0
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        url = f"{self.API_BASE_URL}/cardioscore/date/{start_str}/{end_str}.json"
        
        try:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()
            
            data = response.json()
            
            for reading in data.get('cardioScore', []):
                date_str = reading.get('dateTime')
                if date_str:
                    timestamp = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=ZoneInfo('UTC'))
                    value_data = reading.get('value', {})
                    
                    if 'vo2Max' in value_data:
                        WearableData.objects.update_or_create(
                            device=self.device,
                            patient=self.device.patient,
                            data_type='vo2_max',
                            timestamp=timestamp,
                            defaults={
                                'value': value_data['vo2Max'],
                                'unit': 'mL/kg/min',
                                'metadata': {}
                            }
                        )
                        records_created += 1
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                pass
            else:
                raise
        
        return records_created
    
    def _sync_body_composition(self, start_date, end_date):
        """Sync body composition data (weight, BMI, body fat)"""
        records_created = 0
        current_date = start_date.date()
        end = end_date.date()
        
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            url = f"{self.API_BASE_URL}/body/log/weight/date/{date_str}.json"
            
            try:
                response = requests.get(url, headers=self._get_headers())
                response.raise_for_status()
                
                data = response.json()
                
                for log in data.get('weight', []):
                    timestamp_str = log.get('date') + 'T' + log.get('time', '00:00:00')
                    timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=ZoneInfo('UTC'))
                    
                    if 'weight' in log:
                        WearableData.objects.update_or_create(
                            device=self.device,
                            patient=self.device.patient,
                            data_type='weight',
                            timestamp=timestamp,
                            source_id=str(log.get('logId')),
                            defaults={
                                'value': log['weight'],
                                'unit': 'kg',
                                'metadata': {}
                            }
                        )
                        records_created += 1
                    
                    if 'bmi' in log:
                        WearableData.objects.update_or_create(
                            device=self.device,
                            patient=self.device.patient,
                            data_type='bmi',
                            timestamp=timestamp,
                            source_id=str(log.get('logId')),
                            defaults={
                                'value': log['bmi'],
                                'unit': 'kg/m²',
                                'metadata': {}
                            }
                        )
                        records_created += 1
                    
                    if 'fat' in log:
                        WearableData.objects.update_or_create(
                            device=self.device,
                            patient=self.device.patient,
                            data_type='body_fat',
                            timestamp=timestamp,
                            source_id=str(log.get('logId')),
                            defaults={
                                'value': log['fat'],
                                'unit': '%',
                                'metadata': {}
                            }
                        )
                        records_created += 1
            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code != 404:
                    raise
            
            current_date += timedelta(days=1)
        
        return records_created
    
    def get_intraday_heart_rate(self, date, detail_level='1min'):
        """
        Get intraday heart rate data
        detail_level: '1sec', '1min', '5min', '15min'
        Requires 'Intraday' permission from Fitbit
        """
        date_str = date.strftime('%Y-%m-%d')
        url = f"{self.API_BASE_URL}/activities/heart/date/{date_str}/1d/{detail_level}.json"
        
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        
        return response.json()
    
    def get_device_info(self):
        """Get information about user's Fitbit devices"""
        url = f"{self.API_BASE_URL}/devices.json"
        
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        
        return response.json()


class AppleHealthService:
    """Service to interact with Apple Health"""
    pass
