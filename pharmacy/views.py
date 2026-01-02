from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db import models
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
import uuid
import secrets
import string
from .models import (
    PharmacyInventory, PharmacyOrder, PharmacyOrderItem,
    PharmacySupplier, PharmacyPurchase, PharmacyPurchaseItem,
    PharmacySale, PharmacySaleItem, PharmacyStaff, PharmacyCounter,
    DoctorPharmacyReferral, PharmacyBonusConfig, PharmacyStockMovement
)
from .service_models import PharmacyService
from core.models import Participant
from .serializers import (
    PharmacyInventorySerializer, PharmacyOrderSerializer,
    PharmacySupplierSerializer, PharmacyPurchaseSerializer,
    PharmacySaleSerializer, PharmacyStaffSerializer,
    DoctorPharmacyReferralSerializer, PharmacyBonusConfigSerializer
)
from prescriptions.models import Prescription
from currency_converter.services import CurrencyConverterService

class PharmacyInventoryViewSet(viewsets.ModelViewSet):  # View for PharmacyInventorySet operations
    serializer_class = PharmacyInventorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if self.request.user.role == 'pharmacy':
            return PharmacyInventory.objects.filter(pharmacy=self.request.user).select_related('medication')
        if getattr(self, 'swagger_fake_view', False):
            return PharmacyInventory.objects.none()
        return PharmacyInventory.objects.none()

    def perform_create(self, serializer):  # Perform create
        serializer.save(pharmacy=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'item': serializer.data
        })

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'success': True,
            'message': 'Inventaire mis à jour avec succès',
            'item': serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        medication_name = instance.medication.name if instance.medication else 'Article'
        self.perform_destroy(instance)
        return Response({
            'success': True,
            'message': f'{medication_name} supprimé de l\'inventaire'
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        instance = self.get_object()
        instance.is_publicly_available = True
        instance.save()

        PharmacyStockMovement.objects.create(
            pharmacy=request.user,
            inventory_item=instance,
            movement_type='in',
            quantity=0,
            reason='correction',
            previous_quantity=instance.quantity_in_stock,
            new_quantity=instance.quantity_in_stock,
            performed_by=request.user,
            notes='Article approuvé et rendu disponible'
        )

        return Response({
            'success': True,
            'message': f'{instance.medication.name if instance.medication else "Article"} approuvé et disponible'
        })

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def restock(self, request, pk=None):
        # Use select_for_update to prevent race conditions
        instance = PharmacyInventory.objects.select_for_update().get(pk=pk)
        quantity = request.data.get('quantity', 0)
        batch_number = request.data.get('batch_number', '')
        expiry_date = request.data.get('expiry_date')
        supplier = request.data.get('supplier', '')

        if quantity <= 0:
            return Response({
                'success': False,
                'error': 'La quantité doit être supérieure à 0'
            }, status=status.HTTP_400_BAD_REQUEST)

        previous_quantity = instance.quantity_in_stock
        instance.quantity_in_stock += int(quantity)

        if batch_number:
            instance.batch_number = batch_number
        if expiry_date:
            instance.expiry_date = expiry_date

        instance.save()

        PharmacyStockMovement.objects.create(
            pharmacy=request.user,
            inventory_item=instance,
            movement_type='in',
            quantity=quantity,
            reason='purchase',
            previous_quantity=previous_quantity,
            new_quantity=instance.quantity_in_stock,
            performed_by=request.user,
            notes=f'Réapprovisionnement: +{quantity} unités. Fournisseur: {supplier}'
        )

        article_name = instance.medication.name if instance.medication else "l'article"
        return Response({
            'success': True,
            'message': f'{quantity} unités ajoutées à {article_name}',
            'new_quantity': instance.quantity_in_stock
        })

    @action(detail=False, methods=['get'])
    def low_stock(self, request):  # Low stock
        items = self.get_queryset().filter(quantity_in_stock__lte=models.F('reorder_level'))
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):  # Expiring soon
        from datetime import timedelta
        threshold_date = timezone.now().date() + timedelta(days=30)
        items = self.get_queryset().filter(expiry_date__lte=threshold_date, quantity_in_stock__gt=0)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def download_template(self, request):
        """Download Excel template for inventory import"""
        from django.http import HttpResponse
        from .excel_utils import generate_inventory_template
        
        output = generate_inventory_template()
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="Modele_Inventaire_BINTACURA.xlsx"'
        return response
    
    @action(detail=False, methods=['get'])
    def export_inventory(self, request):
        """Export current inventory to Excel"""
        from django.http import HttpResponse
        from .excel_utils import export_inventory_to_excel
        from datetime import datetime
        
        output = export_inventory_to_excel(request.user)
        
        filename = f"Inventaire_{request.user.full_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    @action(detail=False, methods=['post'])
    def import_inventory(self, request):
        """Import inventory from Excel file"""
        from .excel_utils import import_inventory_from_excel
        
        if 'file' not in request.FILES:
            return Response(
                {'error': 'Aucun fichier fourni'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        
        if not file.name.endswith(('.xlsx', '.xls')):
            return Response(
                {'error': 'Format de fichier invalide. Utilisez .xlsx ou .xls'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = import_inventory_from_excel(file, request.user)
        
        if results['success'] > 0:
            return Response({
                'message': f'{results["success"]} articles importés avec succès',
                'success': results['success'],
                'errors': results['errors'],
                'warnings': results['warnings'],
                'created_medications': results['created_medications']
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Aucun article importé',
                'errors': results['errors']
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[])
    def public_catalog(self, request):  # Public catalog
        pharmacy_id = request.query_params.get('pharmacy_id')
        medication_id = request.query_params.get('medication_id')

        queryset = PharmacyInventory.objects.filter(
            is_publicly_available=True,
            quantity_in_stock__gt=0,
            expiry_date__gt=timezone.now().date()
        ).select_related('medication', 'pharmacy__provider_data')

        if pharmacy_id:
            queryset = queryset.filter(pharmacy_id=pharmacy_id)
        if medication_id:
            queryset = queryset.filter(medication_id=medication_id)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[])
    def check_availability(self, request):  # Check availability
        medication_id = request.query_params.get('medication_id')
        quantity = int(request.query_params.get('quantity', 1))

        if not medication_id:
            return Response({'error': 'medication_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        pharmacies = PharmacyInventory.objects.filter(
            medication_id=medication_id,
            is_publicly_available=True,
            quantity_in_stock__gte=quantity,
            expiry_date__gt=timezone.now().date()
        ).select_related('pharmacy__provider_data').values(
            'pharmacy_id',
            'pharmacy__provider_data__provider_name',
            'pharmacy__provider_data__address',
            'pharmacy__provider_data__phone_number',
            'quantity_in_stock',
            'selling_price'
        )

        return Response(list(pharmacies))

class PharmacyOrderViewSet(viewsets.ModelViewSet):  # View for PharmacyOrderSet operations
    serializer_class = PharmacyOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if self.request.user.role == 'pharmacy':
            return PharmacyOrder.objects.filter(pharmacy=self.request.user).select_related('patient', 'prescription')
        if getattr(self, 'swagger_fake_view', False):
            return PharmacyOrder.objects.none()
        return PharmacyOrder.objects.none()

    def perform_create(self, serializer):  # Perform create
        order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
        serializer.save(pharmacy=self.request.user, order_number=order_number)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):  # Update status
        order = self.get_object()
        new_status = request.data.get('status')

        if new_status in dict(PharmacyOrder.STATUS_CHOICES):
            order.status = new_status
            if new_status == 'ready':
                order.ready_date = timezone.now()
            elif new_status == 'delivered':
                order.delivered_date = timezone.now()
            order.save()
            return Response({'status': 'success', 'message': 'Order status updated'})

        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def process_prescription(self, request, pk=None):  # Process prescription
        try:
            prescription_id = request.data.get('prescription_id')
            prescription = Prescription.objects.get(id=prescription_id)

            order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
            order = PharmacyOrder.objects.create(
                order_number=order_number,
                pharmacy=request.user,
                patient=prescription.patient,
                prescription=prescription,
                status='processing'
            )

            total_amount = 0
            for item in prescription.items.all():
                inventory = PharmacyInventory.objects.filter(
                    pharmacy=request.user,
                    medication=item.medication,
                    quantity_in_stock__gte=item.quantity
                ).first()

                if inventory:
                    order_item = PharmacyOrderItem.objects.create(
                        order=order,
                        medication=item.medication,
                        inventory_item=inventory,
                        quantity=item.quantity,
                        unit_price=inventory.selling_price,
                        total_price=inventory.selling_price * item.quantity,
                        dosage_form=item.dosage_form,
                        strength=item.strength,
                        instructions=item.instructions
                    )
                    total_amount += order_item.total_price

            order.total_amount = total_amount
            order.save()

            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Prescription.DoesNotExist:
            return Response({'error': 'Prescription not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PharmacySupplierViewSet(viewsets.ModelViewSet):  # View for PharmacySupplierSet operations
    serializer_class = PharmacySupplierSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if self.request.user.role == 'pharmacy':
            return PharmacySupplier.objects.filter(pharmacy=self.request.user)
        if getattr(self, 'swagger_fake_view', False):
            return PharmacySupplier.objects.none()
        return PharmacySupplier.objects.none()

    def perform_create(self, serializer):  # Perform create
        serializer.save(pharmacy=self.request.user)

class PharmacyPurchaseViewSet(viewsets.ModelViewSet):  # View for PharmacyPurchaseSet operations
    serializer_class = PharmacyPurchaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if self.request.user.role == 'pharmacy':
            return PharmacyPurchase.objects.filter(pharmacy=self.request.user).select_related('supplier')
        if getattr(self, 'swagger_fake_view', False):
            return PharmacyPurchase.objects.none()
        return PharmacyPurchase.objects.none()

    def perform_create(self, serializer):  # Perform create
        purchase_number = f"PUR-{uuid.uuid4().hex[:10].upper()}"
        serializer.save(pharmacy=self.request.user, purchase_number=purchase_number)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def receive_purchase(self, request, pk=None):  # Receive purchase
        purchase = self.get_object()
        received_items = request.data.get('items', [])

        for item_data in received_items:
            item_id = item_data.get('id')
            quantity_received = item_data.get('quantity_received')
            batch_number = item_data.get('batch_number')
            expiry_date = item_data.get('expiry_date')

            purchase_item = purchase.items.get(id=item_id)
            purchase_item.quantity_received = quantity_received
            purchase_item.batch_number = batch_number
            purchase_item.expiry_date = expiry_date
            purchase_item.save()

            PharmacyInventory.objects.create(
                pharmacy=request.user,
                medication=purchase_item.medication,
                batch_number=batch_number,
                quantity_in_stock=quantity_received,
                unit_price=purchase_item.unit_price,
                selling_price=int(purchase_item.unit_price * 1.3),
                expiry_date=expiry_date
            )

        purchase.status = 'received'
        purchase.received_date = timezone.now().date()
        purchase.save()

        return Response({'status': 'success', 'message': 'Purchase received and inventory updated'})

class PharmacySaleViewSet(viewsets.ModelViewSet):  # View for PharmacySaleSet operations
    serializer_class = PharmacySaleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if self.request.user.role == 'pharmacy':
            return PharmacySale.objects.filter(pharmacy=self.request.user).select_related('patient')
        if getattr(self, 'swagger_fake_view', False):
            return PharmacySale.objects.none()
        return PharmacySale.objects.none()

    @transaction.atomic
    def create(self, request, *args, **kwargs):  # Create
        try:
            sale_number = f"SALE-{uuid.uuid4().hex[:10].upper()}"
            items_data = request.data.get('items', [])

            total_amount = sum(item['total_price'] for item in items_data)
            discount_amount = request.data.get('discount_amount', 0)
            tax_amount = request.data.get('tax_amount', 0)
            final_amount = total_amount - discount_amount + tax_amount

            sale = PharmacySale.objects.create(
                sale_number=sale_number,
                pharmacy=request.user,
                patient_id=request.data.get('patient_id'),
                order_id=request.data.get('order_id'),
                total_amount=total_amount,
                discount_amount=discount_amount,
                tax_amount=tax_amount,
                final_amount=final_amount,
                amount_paid=request.data.get('amount_paid'),
                change_given=request.data.get('change_given', 0),
                payment_method=request.data.get('payment_method'),
                transaction_ref=request.data.get('transaction_ref', ''),
                cashier=request.user
            )

            for item_data in items_data:
                # Use select_for_update to prevent race conditions on inventory
                inventory = PharmacyInventory.objects.select_for_update().get(id=item_data['inventory_item_id'])

                PharmacySaleItem.objects.create(
                    sale=sale,
                    medication_id=item_data['medication_id'],
                    inventory_item=inventory,
                    quantity=item_data['quantity'],
                    unit_price=item_data['unit_price'],
                    total_price=item_data['total_price']
                )

                inventory.quantity_in_stock -= item_data['quantity']
                inventory.save()

            serializer = self.get_serializer(sale)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def daily_sales(self, request):  # Daily sales
        today = timezone.now().date()
        sales = self.get_queryset().filter(sale_date__date=today)
        total = sum(sale.final_amount for sale in sales)

        return Response({
            'count': sales.count(),
            'total': total,
            'sales': self.get_serializer(sales, many=True).data
        })

class PharmacyStaffViewSet(viewsets.ModelViewSet):  # View for PharmacyStaffSet operations
    serializer_class = PharmacyStaffSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):  # Get queryset
        participant = self.request.user
        if getattr(self, 'swagger_fake_view', False):
            return PharmacyStaff.objects.none()
        if participant.role == 'pharmacy':
            queryset = PharmacyStaff.objects.filter(
                pharmacy=participant,
                is_deleted=False
            ).select_related('staff_participant')
            return queryset
        return PharmacyStaff.objects.none()

    def perform_update(self, serializer):
        staff = serializer.save()
        if staff.staff_participant:
            staff.staff_participant.full_name = staff.full_name
            staff.staff_participant.phone_number = staff.phone_number
            staff.staff_participant.email = staff.email
            staff.staff_participant.staff_role = staff.role
            staff.staff_participant.save()

    def perform_destroy(self, instance):
        if instance.staff_participant:
            instance.staff_participant.is_deleted = True
            instance.staff_participant.deleted_at = timezone.now()
            instance.staff_participant.save()
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def toggle_status(self, request, id=None):
        try:
            staff = PharmacyStaff.objects.get(id=id, pharmacy=request.user, is_deleted=False)
            staff.is_active = not staff.is_active
            staff.save()
            
            if staff.staff_participant:
                staff.staff_participant.is_active = staff.is_active
                staff.staff_participant.save()
            
            return Response({
                'status': 'success',
                'is_active': staff.is_active,
                'message': 'Statut mis à jour avec succès'
            })
        except PharmacyStaff.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Personnel non trouvé'
            }, status=404)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=400)

    def perform_create(self, serializer):  # Perform create
        with transaction.atomic():
            staff_data = serializer.validated_data
            
            # Check if participant already exists
            try:
                existing_participant = Participant.objects.get(email=staff_data['email'])
                
                # Check if already a staff member at this pharmacy
                if PharmacyStaff.objects.filter(
                    staff_participant=existing_participant,
                    pharmacy=self.request.user
                ).exists():
                    raise serializers.ValidationError({
                        'email': 'Cet email est déjà utilisé pour un membre du personnel de cette pharmacie.'
                    })
                
                # Check if this person can be made staff
                if existing_participant.role in ['patient', 'doctor']:
                    raise serializers.ValidationError({
                        'email': f'Cette personne est déjà enregistrée comme {existing_participant.get_role_display()}.'
                    })
                
                # Update existing participant to be staff
                existing_participant.role = 'pharmacy'
                existing_participant.staff_role = staff_data['role']
                existing_participant.affiliated_provider_id = self.request.user.uid
                existing_participant.full_name = staff_data['full_name']
                existing_participant.phone_number = staff_data['phone_number']
                
                # Handle password
                auto_generate = staff_data.pop('auto_generate_password', True)
                custom_password = staff_data.pop('password', None)
                
                if auto_generate or not custom_password:
                    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
                    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
                else:
                    temp_password = custom_password
                
                existing_participant.set_password(temp_password)
                existing_participant.save()
                
                user_participant = existing_participant
                
            except Participant.DoesNotExist:
                # Create new participant
                auto_generate = staff_data.pop('auto_generate_password', True)
                custom_password = staff_data.pop('password', None)
                
                if auto_generate or not custom_password:
                    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
                    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))
                else:
                    temp_password = custom_password

                user_participant = Participant.objects.create(
                    email=staff_data['email'],
                    phone_number=staff_data['phone_number'],
                    full_name=staff_data['full_name'],
                    role='pharmacy',
                    password=make_password(temp_password),
                    is_active=True,
                    affiliated_provider_id=self.request.user.uid,
                    staff_role=staff_data['role'],
                )

            # Create pharmacy staff record
            staff = serializer.save(
                pharmacy=self.request.user,
                staff_participant=user_participant
            )
            
            # Send email notification
            try:
                from communication.email_service import EmailService
                EmailService.send_staff_credentials(
                    recipient_email=user_participant.email,
                    staff_name=user_participant.full_name,
                    pharmacy_name=self.request.user.full_name,
                    email=user_participant.email,
                    password=temp_password,
                    role=staff_data['role']
                )
            except Exception as e:
                print(f"Email sending failed: {e}")
            
            # Send SMS notification
            try:
                from communication.notification_service import NotificationService
                message = f"Bienvenue chez {self.request.user.full_name}! Vos accès: Email: {user_participant.email}, Mot de passe: {temp_password}. Connectez-vous sur vitacare.cm"
                NotificationService.send_sms(
                    phone_number=user_participant.phone_number,
                    message=message
                )
            except Exception as e:
                print(f"SMS sending failed: {e}")

class DoctorPharmacyReferralViewSet(viewsets.ModelViewSet):  # View for DoctorPharmacyReferralSet operations
    serializer_class = DoctorPharmacyReferralSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if self.request.user.role == 'doctor':
            return DoctorPharmacyReferral.objects.filter(doctor=self.request.user).select_related('pharmacy', 'patient')
        if getattr(self, 'swagger_fake_view', False):
            return DoctorPharmacyReferral.objects.none()
        elif self.request.user.role == 'pharmacy':
            return DoctorPharmacyReferral.objects.filter(pharmacy=self.request.user).select_related('doctor', 'patient')
        return DoctorPharmacyReferral.objects.none()

    @action(detail=False, methods=['get'])
    def my_bonuses(self, request):  # My bonuses
        if request.user.role != 'doctor':
            return Response({'error': 'Only doctors can access bonuses'}, status=status.HTTP_403_FORBIDDEN)

        referrals = self.get_queryset()
        total_earned = referrals.filter(bonus_paid=False).aggregate(total=models.Sum('bonus_earned'))['total'] or 0
        total_paid = referrals.filter(bonus_paid=True).aggregate(total=models.Sum('bonus_earned'))['total'] or 0

        return Response({
            'total_earned': total_earned,
            'total_paid': total_paid,
            'pending_payment': total_earned,
            'referrals': self.get_serializer(referrals.order_by('-referral_date')[:20], many=True).data
        })

    @action(detail=False, methods=['post'])
    def request_payment(self, request):  # Request payment
        if request.user.role != 'doctor':
            return Response({'error': 'Only doctors can request payments'}, status=status.HTTP_403_FORBIDDEN)

        pharmacy_id = request.data.get('pharmacy_id')
        if not pharmacy_id:
            return Response({'error': 'pharmacy_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        unpaid = DoctorPharmacyReferral.objects.filter(
            doctor=request.user,
            pharmacy_id=pharmacy_id,
            bonus_paid=False,
            was_fulfilled=True
        )

        total_amount = unpaid.aggregate(total=models.Sum('bonus_earned'))['total'] or 0

        return Response({
            'success': True,
            'pharmacy_id': pharmacy_id,
            'total_amount': total_amount,
            'referrals_count': unpaid.count(),
            'message': 'Payment request created. Pharmacy will process your request.'
        })

class PharmacyBonusConfigViewSet(viewsets.ModelViewSet):  # View for PharmacyBonusConfigSet operations
    serializer_class = PharmacyBonusConfigSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):  # Get queryset
        if self.request.user.role == 'pharmacy':
            return PharmacyBonusConfig.objects.filter(pharmacy=self.request.user).select_related('doctor')
        if getattr(self, 'swagger_fake_view', False):
            return PharmacyBonusConfig.objects.none()
        return PharmacyBonusConfig.objects.none()

    def perform_create(self, serializer):  # Perform create
        serializer.save(pharmacy=self.request.user)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def calculate_bonuses(self, request):  # Calculate bonuses
        if request.user.role != 'pharmacy':
            return Response({'error': 'Only pharmacies can calculate bonuses'}, status=status.HTTP_403_FORBIDDEN)

        month = request.data.get('month', timezone.now().month)
        year = request.data.get('year', timezone.now().year)

        start_date = timezone.datetime(year, month, 1)
        if month == 12:
            end_date = timezone.datetime(year + 1, 1, 1)
        else:
            end_date = timezone.datetime(year, month + 1, 1)

        configs = PharmacyBonusConfig.objects.filter(
            pharmacy=request.user,
            is_active=True,
            valid_from__lte=start_date.date()
        ).filter(
            models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=end_date.date())
        )

        for config in configs:
            referrals = DoctorPharmacyReferral.objects.filter(
                pharmacy=request.user,
                doctor=config.doctor if config.doctor else models.F('doctor'),
                referral_date__gte=start_date,
                referral_date__lt=end_date,
                was_fulfilled=True,
                bonus_earned=0
            )

            count = referrals.count()

            if config.bonus_type == 'percentage':
                for referral in referrals:
                    bonus = int(referral.total_amount * float(config.bonus_percentage) / 100)
                    referral.bonus_earned = bonus
                    referral.save()

            elif config.bonus_type == 'fixed_amount':
                for referral in referrals:
                    referral.bonus_earned = config.fixed_bonus_amount
                    referral.save()

            elif config.bonus_type == 'tiered':
                if config.min_prescriptions_per_month <= count <= config.max_prescriptions_per_month:
                    for referral in referrals:
                        referral.bonus_earned = config.bonus_amount_for_tier
                        referral.save()

        return Response({
            'success': True,
            'message': f'Bonuses calculated for {month}/{year}',
            'configs_applied': configs.count()
        })


# Staff Management Views
@login_required
def staff_list(request):
    """Pharmacy owner staff management page"""
    # Only pharmacy owners (without staff_role) can manage staff
    if request.user.role != 'pharmacy':
        messages.error(request, 'Accès refusé. Réservé aux propriétaires de pharmacie.')
        return redirect('/')
    
    # If user has staff_role, they are staff, not owner
    if request.user.staff_role:
        messages.error(request, 'Accès refusé. Cette page est réservée aux propriétaires de pharmacie.')
        return redirect('/pharmacy/staff/counter/')
    
    staff_members = PharmacyStaff.objects.filter(
        pharmacy=request.user
    ).select_related('staff_participant', 'assigned_counter').order_by('-created_at')
    
    counters = PharmacyCounter.objects.filter(pharmacy=request.user, is_active=True)
    
    context = {
        'staff_members': staff_members,
        'counters': counters,
        'total_staff': staff_members.count(),
        'active_staff': staff_members.filter(is_active=True).count(),
    }
    
    return render(request, 'pharmacy/staff/staff_list.html', context)


# Counter Dashboard Views
@login_required
def counter_dashboard(request):
    """Pharmacy staff counter dashboard"""
    # Check if user is pharmacy role
    if request.user.role != 'pharmacy':
        messages.error(request, 'Accès refusé. Vous devez être un membre du personnel de pharmacie.')
        return redirect('/')
    
    # Check if user has staff_role (distinguishes staff from owner)
    if not request.user.staff_role:
        messages.error(request, 'Accès refusé. Cette page est réservée au personnel de pharmacie.')
        return redirect('/pharmacy/dashboard/')
    
    # For pharmacy staff, use affiliated_provider_id to get pharmacy
    pharmacy_id = request.user.affiliated_provider_id
    if not pharmacy_id:
        messages.error(request, 'Aucune affiliation à une pharmacie trouvée. Veuillez contacter l\'administrateur.')
        return redirect('/')
    
    try:
        pharmacy = Participant.objects.get(uid=pharmacy_id, role='pharmacy')
    except Participant.DoesNotExist:
        messages.error(request, 'Pharmacie non trouvée. Veuillez contacter l\'administrateur.')
        return redirect('/')
    
    today = timezone.now().date()
    pending_orders = PharmacyOrder.objects.filter(
        pharmacy=pharmacy,
        status='pending',
        created_at__date=today
    ).select_related('prescription__patient', 'prescription__doctor')
    
    processed_today = PharmacyOrder.objects.filter(
        pharmacy=pharmacy,
        status__in=['ready', 'delivered'],
        updated_at__date=today
    ).count()
    
    context = {
        'staff_name': request.user.full_name,
        'staff_role': request.user.staff_role,
        'pharmacy_name': pharmacy.full_name,
        'pending_orders': pending_orders,
        'pending_count': pending_orders.count(),
        'today_processed_count': processed_today,
    }
    
    return render(request, 'pharmacy/staff/counter_dashboard.html', context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_prescription(request):
    """Search prescription by QR code or manual code"""
    code = request.GET.get('code')
    
    if not code:
        return Response({
            'success': False,
            'message': 'Code is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        prescription = Prescription.objects.get(
            models.Q(prescription_number=code) | models.Q(qr_code=code)
        )
        
        currency_service = CurrencyConverterService()
        local_currency = currency_service.get_participant_currency(prescription.patient)
        
        medications = []
        for item in prescription.items.all():
            staff = PharmacyStaff.objects.filter(staff_participant=request.user).first()
            if not staff:
                continue
                
            inventory = PharmacyInventory.objects.filter(
                pharmacy=staff.pharmacy,
                medication=item.medication,
                quantity_in_stock__gte=item.quantity
            ).first()
            
            if inventory:
                local_price = currency_service.convert_to_local(
                    inventory.selling_price,
                    prescription.patient
                )
                medications.append({
                    'medicine_name': item.medication.name,
                    'quantity': item.quantity,
                    'unit_price': local_price,
                    'currency': local_currency,
                    'available': True
                })
            else:
                medications.append({
                    'medicine_name': item.medication.name,
                    'quantity': item.quantity,
                    'unit_price': 0,
                    'currency': local_currency,
                    'available': False
                })
        
        return Response({
            'success': True,
            'prescription': {
                'id': str(prescription.id),
                'prescription_number': prescription.prescription_number,
                'patient_name': prescription.patient.full_name,
                'patient_phone': prescription.patient.phone_number,
                'status': prescription.status,
                'currency': local_currency,
                'medications': medications
            }
        })
        
    except Prescription.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Prescription not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def prepare_prescription(request, prescription_id):
    """Prepare medications for prescription"""
    try:
        prescription = get_object_or_404(Prescription, id=prescription_id)
        counter_id = request.data.get('counter_id')
        
        staff = PharmacyStaff.objects.filter(staff_participant=request.user).first()
        if not staff:
            return Response({
                'success': False,
                'message': 'Staff record not found'
            }, status=status.HTTP_403_FORBIDDEN)
        
        order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
        order = PharmacyOrder.objects.create(
            order_number=order_number,
            pharmacy=staff.pharmacy,
            patient=prescription.patient,
            prescription=prescription,
            status='processing',
            delivery_method='pickup'
        )
        
        currency_service = CurrencyConverterService()
        total_usd = 0
        
        for item in prescription.items.all():
            inventory = PharmacyInventory.objects.filter(
                pharmacy=staff.pharmacy,
                medication=item.medication,
                quantity_in_stock__gte=item.quantity
            ).first()
            
            if not inventory:
                order.delete()
                return Response({
                    'success': False,
                    'message': f'Insufficient stock for {item.medication.name}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            item_total_usd = inventory.selling_price * item.quantity
            total_usd += item_total_usd
            
            PharmacyOrderItem.objects.create(
                order=order,
                medicine=item.medication,
                inventory_item=inventory,
                quantity=item.quantity,
                unit_price_usd=inventory.selling_price,
                total_price_usd=item_total_usd
            )
        
        order.total_amount_usd = total_usd
        order.save()
        
        return Response({
            'success': True,
            'message': 'Medications prepared successfully',
            'order_id': str(order.id)
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required
def payment_processing(request, order_id):
    """Payment processing page"""
    order = get_object_or_404(PharmacyOrder, id=order_id)
    
    currency_service = CurrencyConverterService()
    local_currency = currency_service.get_participant_currency(order.patient)
    
    for item in order.items.all():
        item.unit_price_local = currency_service.convert_to_local(
            item.unit_price_usd,
            order.patient
        )
        item.total_price_local = currency_service.convert_to_local(
            item.total_price_usd,
            order.patient
        )
    
    order.subtotal_local = currency_service.convert_to_local(
        order.total_amount_usd,
        order.patient
    )
    order.discount_amount_local = currency_service.convert_to_local(
        order.discount_amount_usd or 0,
        order.patient
    )
    order.insurance_coverage_local = currency_service.convert_to_local(
        order.insurance_coverage_usd or 0,
        order.patient
    )
    order.final_amount_local = currency_service.convert_to_local(
        order.final_amount_usd,
        order.patient
    )
    order.local_currency = local_currency
    
    context = {
        'order': order,
    }
    
    return render(request, 'pharmacy/staff/payment_processing.html', context)



class PharmacyServiceViewSet(viewsets.ModelViewSet):
    """CRUD operations for pharmacy services with currency conversion"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role == 'pharmacy':
            return PharmacyService.objects.filter(pharmacy=self.request.user)
        if getattr(self, 'swagger_fake_view', False):
            return PharmacyService.objects.none()
        return PharmacyService.objects.none()
    
    @transaction.atomic
    def perform_create(self, serializer):
        from currency_converter.utils import convert_to_xof
        
        pharmacy = self.request.user
        if not pharmacy.is_verified:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Votre compte doit être vérifié pour créer des services")
        
        price_input = self.request.data.get('price', 0)
        currency_input = self.request.data.get('currency', 'XOF')
        
        price_in_xof_cents = convert_to_xof(price_input, currency_input)
        
        serializer.save(
            pharmacy=pharmacy,
            price=price_in_xof_cents,
            currency='XOF',
            region_code=pharmacy.region_code or 'global'
        )
    
    @transaction.atomic
    def perform_update(self, serializer):
        from currency_converter.utils import convert_to_xof
        
        if 'price' in self.request.data:
            price_input = self.request.data.get('price', 0)
            currency_input = self.request.data.get('currency', 'XOF')
            price_in_xof_cents = convert_to_xof(price_input, currency_input)
            serializer.save(price=price_in_xof_cents, currency='XOF')
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category = request.query_params.get('category')
        if category:
            services = self.get_queryset().filter(category=category, is_active=True)
            from rest_framework.serializers import ModelSerializer
            
            class ServiceSerializer(ModelSerializer):
                class Meta:
                    model = PharmacyService
                    fields = '__all__'
            
            serializer = ServiceSerializer(services, many=True)
            return Response(serializer.data)
        return Response({'error': 'category required'}, status=status.HTTP_400_BAD_REQUEST)
