from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from django.db import transaction, models
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
import logging

from .models import PharmacyOrder, PharmacyOrderItem, PharmacyInventory
from .serializers import PharmacyOrderSerializer
from core.models import Participant
from prescriptions.models import Medication
from currency_converter.services import CurrencyConverterService

logger = logging.getLogger(__name__)


@extend_schema(tags=["Shopping Cart"])
class ShoppingCartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PharmacyOrderSerializer

    def get_or_create_cart(self, patient, pharmacy=None):
        cart = PharmacyOrder.objects.filter(
            patient=patient,
            status='cart'
        ).first()

        if not cart and pharmacy:
            # Get pharmacy's currency for the order
            pharmacy_currency = CurrencyConverterService.get_participant_currency(pharmacy)
            
            order_number = f'CART-{patient.uid.hex[:8]}-{datetime.now().strftime("%Y%m%d%H%M%S")}'
            cart = PharmacyOrder.objects.create(
                order_number=order_number,
                pharmacy=pharmacy,
                patient=patient,
                status='cart',
                payment_status='unpaid',
                delivery_method='pickup',
                currency=pharmacy_currency
            )
        return cart

    @action(detail=False, methods=['get'])
    def my_cart(self, request):
        participant = request.user
        if participant.role != 'patient':
            return Response(
                {'detail': 'Seuls les patients peuvent avoir un panier'},
                status=status.HTTP_403_FORBIDDEN
            )

        cart = self.get_or_create_cart(participant)
        if not cart:
            return Response({
                'success': True,
                'cart': None,
                'items': [],
                'total': 0,
                'item_count': 0
            })

        # Get patient's currency for display
        patient_currency = CurrencyConverterService.get_participant_currency(participant)
        order_currency = cart.currency if cart.currency else 'USD'

        items = PharmacyOrderItem.objects.filter(order=cart).select_related(
            'medication', 'inventory_item'
        )

        items_data = []
        total = 0
        for item in items:
            item_total = item.total_price
            total += item_total
            
            # Convert prices for display
            unit_price_major = Decimal(str(item.unit_price)) / 100
            total_price_major = Decimal(str(item_total)) / 100
            
            # Convert to patient currency if different
            if patient_currency != order_currency:
                unit_price_display = CurrencyConverterService.convert(
                    unit_price_major,
                    order_currency,
                    patient_currency
                )
                total_price_display = CurrencyConverterService.convert(
                    total_price_major,
                    order_currency,
                    patient_currency
                )
            else:
                unit_price_display = unit_price_major
                total_price_display = total_price_major
            
            items_data.append({
                'id': str(item.id),
                'medication_name': item.medication.name if item.medication else 'N/A',
                'medication_id': str(item.medication.id) if item.medication else None,
                'inventory_id': str(item.inventory_item.id) if item.inventory_item else None,
                'quantity': item.quantity,
                'unit_price': float(unit_price_display),
                'total_price': float(total_price_display),
                'currency': patient_currency,
                'dosage_form': item.dosage_form,
                'strength': item.strength
            })

        # Convert total for display
        total_major = Decimal(str(total)) / 100
        if patient_currency != order_currency:
            total_display = CurrencyConverterService.convert(
                total_major,
                order_currency,
                patient_currency
            )
        else:
            total_display = total_major

        return Response({
            'success': True,
            'cart': {
                'id': str(cart.id),
                'pharmacy_id': str(cart.pharmacy.uid) if cart.pharmacy else None,
                'pharmacy_name': cart.pharmacy.full_name if cart.pharmacy else None,
                'delivery_method': cart.delivery_method,
                'delivery_address': cart.delivery_address,
                'delivery_fee': float(Decimal(str(cart.delivery_fee)) / 100),
                'total_amount': float(total_display),
                'currency': patient_currency
            },
            'items': items_data,
            'total': float(total_display),
            'item_count': len(items_data)
        })

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        participant = request.user
        if participant.role != 'patient':
            return Response(
                {'detail': 'Seuls les patients peuvent ajouter au panier'},
                status=status.HTTP_403_FORBIDDEN
            )

        inventory_id = request.data.get('inventory_id')
        quantity = request.data.get('quantity', 1)

        if not inventory_id:
            return Response(
                {'detail': 'inventory_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            inventory_item = PharmacyInventory.objects.select_related('pharmacy', 'medication').get(id=inventory_id)
        except PharmacyInventory.DoesNotExist:
            return Response(
                {'detail': 'Article non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

        if inventory_item.quantity_in_stock < quantity:
            return Response(
                {'detail': f'Stock insuffisant. Disponible: {inventory_item.quantity_in_stock}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            cart = self.get_or_create_cart(participant, inventory_item.pharmacy)

            existing_item = PharmacyOrderItem.objects.filter(
                order=cart,
                medication=inventory_item.medication,
                inventory_item=inventory_item
            ).first()

            if existing_item:
                existing_item.quantity += quantity
                total_price = existing_item.quantity * inventory_item.selling_price
                existing_item.total_price = total_price
                existing_item.save()
                message = 'Quantité mise à jour'
            else:
                total_price = quantity * inventory_item.selling_price
                PharmacyOrderItem.objects.create(
                    order=cart,
                    medication=inventory_item.medication,
                    inventory_item=inventory_item,
                    quantity=quantity,
                    unit_price=inventory_item.selling_price,
                    total_price=total_price,
                    dosage_form=inventory_item.medication.dosage_forms[0] if inventory_item.medication.dosage_forms else '',
                    strength=inventory_item.medication.strengths[0] if inventory_item.medication.strengths else ''
                )
                message = 'Article ajouté au panier'

            cart_total = PharmacyOrderItem.objects.filter(order=cart).aggregate(
                total=models.Sum('total_price')
            )['total'] or 0
            cart.total_amount = cart_total
            cart.save()

        return Response({
            'success': True,
            'message': message,
            'cart_total': cart_total
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def update_quantity(self, request):
        participant = request.user
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity', 1)

        if not item_id:
            return Response(
                {'detail': 'item_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            item = PharmacyOrderItem.objects.select_related('order', 'inventory_item').get(
                id=item_id,
                order__patient=participant,
                order__status='cart'
            )
        except PharmacyOrderItem.DoesNotExist:
            return Response(
                {'detail': 'Article non trouvé dans le panier'},
                status=status.HTTP_404_NOT_FOUND
            )

        if quantity <= 0:
            item.delete()
            message = 'Article retiré du panier'
        else:
            if item.inventory_item and item.inventory_item.quantity_in_stock < quantity:
                return Response(
                    {'detail': f'Stock insuffisant. Disponible: {item.inventory_item.quantity_in_stock}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            item.quantity = quantity
            item.total_price = quantity * item.unit_price
            item.save()
            message = 'Quantité mise à jour'

        cart = item.order
        cart_total = PharmacyOrderItem.objects.filter(order=cart).aggregate(
            total=models.Sum('total_price')
        )['total'] or 0
        cart.total_amount = cart_total
        cart.save()

        return Response({
            'success': True,
            'message': message,
            'cart_total': cart_total
        })

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        participant = request.user
        item_id = request.data.get('item_id')

        if not item_id:
            return Response(
                {'detail': 'item_id est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            item = PharmacyOrderItem.objects.select_related('order').get(
                id=item_id,
                order__patient=participant,
                order__status='cart'
            )
        except PharmacyOrderItem.DoesNotExist:
            return Response(
                {'detail': 'Article non trouvé dans le panier'},
                status=status.HTTP_404_NOT_FOUND
            )

        cart = item.order
        item.delete()

        cart_total = PharmacyOrderItem.objects.filter(order=cart).aggregate(
            total=models.Sum('total_price')
        )['total'] or 0
        cart.total_amount = cart_total
        cart.save()

        return Response({
            'success': True,
            'message': 'Article retiré du panier',
            'cart_total': cart_total
        })

    @action(detail=False, methods=['post'])
    def update_delivery(self, request):
        participant = request.user
        if participant.role != 'patient':
            return Response(
                {'detail': 'Seuls les patients peuvent modifier la livraison'},
                status=status.HTTP_403_FORBIDDEN
            )

        cart = self.get_or_create_cart(participant)
        if not cart:
            return Response(
                {'detail': 'Panier non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

        delivery_method = request.data.get('delivery_method', 'pickup')
        delivery_address = request.data.get('delivery_address', '')

        cart.delivery_method = delivery_method
        cart.delivery_address = delivery_address

        if delivery_method == 'delivery':
            patient_lat = participant.latitude
            patient_lon = participant.longitude
            pharmacy_lat = cart.pharmacy.latitude if cart.pharmacy else None
            pharmacy_lon = cart.pharmacy.longitude if cart.pharmacy else None

            if patient_lat and patient_lon and pharmacy_lat and pharmacy_lon:
                from math import radians, sin, cos, sqrt, atan2
                R = 6371
                lat1, lon1 = radians(patient_lat), radians(patient_lon)
                lat2, lon2 = radians(pharmacy_lat), radians(pharmacy_lon)
                dlat, dlon = lat2 - lat1, lon2 - lon1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distance_km = R * c

                # Base delivery fees in USD
                if distance_km <= 5:
                    base_fee_usd = Decimal('1.50')
                elif distance_km <= 10:
                    base_fee_usd = Decimal('3.00')
                elif distance_km <= 20:
                    base_fee_usd = Decimal('5.00')
                else:
                    base_fee_usd = Decimal('8.00')
                
                # Convert to pharmacy currency
                pharmacy_currency = CurrencyConverterService.get_participant_currency(cart.pharmacy)
                if pharmacy_currency != 'USD':
                    fee_in_pharmacy_currency = CurrencyConverterService.convert(
                        base_fee_usd,
                        'USD',
                        pharmacy_currency
                    )
                else:
                    fee_in_pharmacy_currency = base_fee_usd
                
                # Store in minor units
                cart.delivery_fee = int(fee_in_pharmacy_currency * 100)
            else:
                # Default fee: $3.00 USD
                base_fee_usd = Decimal('3.00')
                pharmacy_currency = CurrencyConverterService.get_participant_currency(cart.pharmacy)
                if pharmacy_currency != 'USD':
                    fee_in_pharmacy_currency = CurrencyConverterService.convert(
                        base_fee_usd,
                        'USD',
                        pharmacy_currency
                    )
                else:
                    fee_in_pharmacy_currency = base_fee_usd
                cart.delivery_fee = int(fee_in_pharmacy_currency * 100)
        else:
            cart.delivery_fee = 0

        cart.save()

        return Response({
            'success': True,
            'message': 'Mode de livraison mis à jour',
            'delivery_fee': float(Decimal(str(cart.delivery_fee)) / 100),
            'total_amount': float((Decimal(str(cart.total_amount)) + Decimal(str(cart.delivery_fee))) / 100),
            'currency': cart.currency if cart.currency else 'USD'
        })

    @action(detail=False, methods=['post'])
    def clear_cart(self, request):
        participant = request.user
        cart = self.get_or_create_cart(participant)
        if cart:
            PharmacyOrderItem.objects.filter(order=cart).delete()
            cart.total_amount = 0
            cart.save()

        return Response({
            'success': True,
            'message': 'Panier vidé'
        })
