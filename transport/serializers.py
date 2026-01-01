from rest_framework import serializers
from .models import TransportRequest, TransportProvider, RideShareQuote, RideShareProvider
from core.models import Participant
from currency_converter.services import CurrencyConverterService
from decimal import Decimal


class TransportRequestSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    patient_email = serializers.EmailField(source="patient.email", read_only=True)
    estimated_distance_display = serializers.SerializerMethodField()
    estimated_cost_local = serializers.SerializerMethodField()
    final_cost_local = serializers.SerializerMethodField()
    patient_currency = serializers.SerializerMethodField()

    class Meta:
        model = TransportRequest
        fields = [
            "id",
            "request_number",
            "patient",
            "patient_name",
            "patient_email",
            "transport_type",
            "urgency",
            "status",
            "pickup_address",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_address",
            "dropoff_latitude",
            "dropoff_longitude",
            "scheduled_pickup_time",
            "actual_pickup_time",
            "actual_dropoff_time",
            "driver_id",
            "driver_name",
            "driver_phone",
            "vehicle_number",
            "estimated_cost",
            "final_cost",
            "payment_status",
            "payment_id",
            "patient_notes",
            "special_requirements",
            "medical_equipment_needed",
            "companion_count",
            "companion_names",
            "estimated_distance",
            "estimated_distance_display",
            "estimated_duration",
            "estimated_cost_local",
            "final_cost_local",
            "patient_currency",
            "current_latitude",
            "current_longitude",
            "last_location_update",
            "rating",
            "feedback",
            "created_at",
            "updated_at",
            "cancelled_at",
            "cancellation_reason",
        ]
        read_only_fields = [
            "id",
            "request_number",
            "patient",
            "scheduled_pickup_time",
            "created_at",
            "updated_at",
            "last_location_update"
        ]

    def get_patient_name(self, obj):
        return obj.patient.full_name or obj.patient.email

    def get_estimated_distance_display(self, obj):
        if obj.estimated_distance:
            return f"{obj.estimated_distance} km"
        return None

    def get_patient_currency(self, obj):
        """Get patient's local currency"""
        return CurrencyConverterService.get_participant_currency(obj.patient)

    def get_estimated_cost_local(self, obj):
        """Get estimated cost in patient's local currency"""
        if not obj.estimated_cost:
            return None

        base_currency = 'USD'  # All prices stored in USD
        patient_currency = CurrencyConverterService.get_participant_currency(obj.patient)
        amount = Decimal(str(obj.estimated_cost))

        # Convert to patient's currency if needed
        if base_currency != patient_currency:
            conversion_result = CurrencyConverterService.convert(amount, base_currency, patient_currency)
            converted_amount = conversion_result['converted_amount']
        else:
            converted_amount = amount

        return {
            'amount': float(converted_amount),
            'currency': patient_currency,
            'formatted': CurrencyConverterService.format_amount(converted_amount, patient_currency),
            'original_amount': float(amount),
            'original_currency': base_currency,
            'needs_conversion': base_currency != patient_currency
        }

    def get_final_cost_local(self, obj):
        """Get final cost in patient's local currency"""
        if not obj.final_cost:
            return None

        base_currency = 'USD'
        patient_currency = CurrencyConverterService.get_participant_currency(obj.patient)
        amount = Decimal(str(obj.final_cost))

        # Convert to patient's currency if needed
        if base_currency != patient_currency:
            conversion_result = CurrencyConverterService.convert(amount, base_currency, patient_currency)
            converted_amount = conversion_result['converted_amount']
        else:
            converted_amount = amount

        return {
            'amount': float(converted_amount),
            'currency': patient_currency,
            'formatted': CurrencyConverterService.format_amount(converted_amount, patient_currency),
            'original_amount': float(amount),
            'original_currency': base_currency,
            'needs_conversion': base_currency != patient_currency
        }

    def create(self, validated_data):
        # Calculate estimated cost if coordinates are available
        if (validated_data.get('pickup_latitude') and validated_data.get('pickup_longitude') and
            validated_data.get('dropoff_latitude') and validated_data.get('dropoff_longitude')):

            from math import radians, sin, cos, sqrt, atan2
            
            # Calculate distance using Haversine formula
            lat1, lon1 = validated_data['pickup_latitude'], validated_data['pickup_longitude']
            lat2, lon2 = validated_data['dropoff_latitude'], validated_data['dropoff_longitude']
            
            R = 6371  # Earth's radius in km
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c
            
            validated_data['estimated_distance'] = round(distance, 2)
            
            # Estimate duration (assuming average speed of 40 km/h)
            validated_data['estimated_duration'] = int((distance / 40) * 60)
            
            # Calculate estimated cost
            transport_type = validated_data.get('transport_type', 'medical_taxi')
            base_cost = 50 if transport_type == 'ambulance' else 30
            cost_per_km = 2.5 if transport_type == 'ambulance' else 1.5
            validated_data['estimated_cost'] = round(base_cost + (distance * cost_per_km), 2)

        return super().create(validated_data)


class TransportProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportProvider
        fields = '__all__'


class RideShareProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideShareProvider
        fields = ['id', 'name', 'is_active', 'average_rating']


class RideShareQuoteSerializer(serializers.ModelSerializer):
    provider = RideShareProviderSerializer(read_only=True)
    total_fare_local = serializers.SerializerMethodField()
    patient_currency = serializers.SerializerMethodField()

    class Meta:
        model = RideShareQuote
        fields = [
            'id',
            'provider',
            'vehicle_type',
            'base_fare',
            'distance_fare',
            'surge_multiplier',
            'total_fare',
            'currency',
            'total_fare_local',
            'patient_currency',
            'driver_name',
            'driver_photo_url',
            'driver_rating',
            'driver_phone',
            'vehicle_make',
            'vehicle_model',
            'vehicle_color',
            'vehicle_plate',
            'vehicle_capacity',
            'estimated_arrival_minutes',
            'estimated_trip_duration_minutes',
            'status',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_patient_currency(self, obj):
        """Get patient's local currency"""
        return CurrencyConverterService.get_participant_currency(obj.transport_request.patient)

    def get_total_fare_local(self, obj):
        """Get total fare in patient's local currency"""
        patient_currency = CurrencyConverterService.get_participant_currency(obj.transport_request.patient)

        # Convert to patient's currency if needed
        if obj.currency != patient_currency:
            conversion_result = CurrencyConverterService.convert(obj.total_fare, obj.currency, patient_currency)
            converted_amount = conversion_result['converted_amount']
            exchange_rate = CurrencyConverterService.get_rate(obj.currency, patient_currency)
        else:
            converted_amount = obj.total_fare
            exchange_rate = Decimal('1.0')

        return {
            'amount': float(converted_amount),
            'currency': patient_currency,
            'formatted': CurrencyConverterService.format_amount(converted_amount, patient_currency),
            'original_amount': float(obj.total_fare),
            'original_currency': obj.currency,
            'needs_conversion': obj.currency != patient_currency,
            'exchange_rate': float(exchange_rate)
        }
