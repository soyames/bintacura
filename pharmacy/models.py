from django.db import models
from django.utils import timezone
import uuid
from core.models import Participant
from core.mixins import SyncMixin
from prescriptions.models import Medication
from pharmacy.service_models import PharmacyService


class PharmacyData(models.Model):
    """
    Pharmacy profile data - OneToOne extension of Participant.
    Stores pharmacy-specific information including license and services.
    Does not use SyncMixin as it syncs with the parent Participant.
    """
    participant = models.OneToOneField(
        Participant, on_delete=models.CASCADE, related_name="pharmacy_data"
    )
    license_number = models.CharField(max_length=100, unique=True)
    registration_number = models.CharField(max_length=100, blank=True)
    consultation_fee = models.IntegerField(default=0)  # For pharmacist consultations
    has_delivery = models.BooleanField(default=False)
    delivery_radius_km = models.IntegerField(default=0)
    accepts_prescriptions = models.BooleanField(default=True)
    has_refrigeration = models.BooleanField(default=False)
    operates_24_7 = models.BooleanField(default=False)
    operating_hours = models.JSONField(default=dict)
    services_offered = models.JSONField(default=list)
    rating = models.FloatField(default=0.0)
    total_reviews = models.IntegerField(default=0)
    
    class Meta:
        db_table = "pharmacy_data"
    
    def __str__(self):
        return f"{self.participant.full_name} - Pharmacy"
    
    def get_actual_rating(self):
        """Calculate real-time average rating from Review model"""
        from core.models import Review
        from django.db.models import Avg
        
        reviews = Review.objects.filter(
            reviewed_type='pharmacy',
            reviewed_id=self.participant.uid,
            is_approved=True
        )
        
        if not reviews.exists():
            return 0.0
            
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg_rating, 2) if avg_rating else 0.0


class PharmacyInventory(SyncMixin):  # Manages pharmacy medication stock and inventory levels
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='inventory_items')
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='inventory_items')
    batch_number = models.CharField(max_length=100)
    quantity_in_stock = models.IntegerField(default=0)
    unit_price = models.IntegerField(default=0)
    selling_price = models.IntegerField(default=0)
    manufacturer = models.CharField(max_length=255, blank=True)
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField()
    reorder_level = models.IntegerField(default=10)
    storage_location = models.CharField(max_length=100, blank=True)
    requires_refrigeration = models.BooleanField(default=False)
    is_publicly_available = models.BooleanField(default=True)

    class Meta:  # Meta class implementation
        db_table = 'pharmacy_inventory'
        indexes = [
            models.Index(fields=['pharmacy', 'medication']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['quantity_in_stock']),
            models.Index(fields=['is_publicly_available']),
        ]

class PharmacyOrder(SyncMixin):  # Tracks customer medication orders and fulfillment status
    STATUS_CHOICES = [
        ('cart', 'Shopping Cart'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('ready', 'Ready for Pickup'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('cash_on_delivery', 'Cash on Delivery'),
        ('card', 'Card'),
        ('mobile_money', 'Mobile Money'),
        ('insurance', 'Insurance'),
        # NO WALLET - BINTACURA does not store money, all payments via external gateways
    ]

    order_number = models.CharField(max_length=50, unique=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='pharmacy_orders')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='pharmacy_patient_orders')
    prescription = models.ForeignKey('prescriptions.Prescription', on_delete=models.SET_NULL, null=True, blank=True, related_name='pharmacy_orders')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='cash_on_delivery', help_text='Payment method selected by patient')
    payment_reference = models.CharField(max_length=100, blank=True, help_text='Payment transaction reference number')
    total_amount = models.IntegerField(default=0)
    currency = models.CharField(max_length=3, default='XOF', help_text='Currency code for this order')
    amount_paid = models.IntegerField(default=0)
    insurance_covered = models.IntegerField(default=0)
    delivery_method = models.CharField(max_length=50, default='pickup')
    delivery_address = models.TextField(blank=True)
    delivery_fee = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    order_date = models.DateTimeField(default=timezone.now)
    ready_date = models.DateTimeField(null=True, blank=True)
    delivered_date = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = 'pharmacy_orders'
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['pharmacy', 'status']),
            models.Index(fields=['patient']),
            models.Index(fields=['order_number']),
            models.Index(fields=['order_date']),
        ]

class PharmacyOrderItem(SyncMixin):  # Represents individual medications in a pharmacy order
    order = models.ForeignKey(PharmacyOrder, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT)
    inventory_item = models.ForeignKey(PharmacyInventory, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField()
    unit_price = models.IntegerField()
    total_price = models.IntegerField()
    dosage_form = models.CharField(max_length=50, blank=True)
    strength = models.CharField(max_length=50, blank=True)
    instructions = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = 'pharmacy_order_items'

class PharmacySupplier(SyncMixin):  # Stores information about pharmacy medication suppliers
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='suppliers')
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    license_number = models.CharField(max_length=100, blank=True)
    payment_terms = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:  # Meta class implementation
        db_table = 'pharmacy_suppliers'
        indexes = [
            models.Index(fields=['pharmacy', 'is_active']),
        ]

class PharmacyPurchase(SyncMixin):  # Tracks pharmacy purchase orders from suppliers
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('partially_received', 'Partially Received'),
        ('cancelled', 'Cancelled'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    purchase_number = models.CharField(max_length=50, unique=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='purchases')
    supplier = models.ForeignKey(PharmacySupplier, on_delete=models.PROTECT)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    order_date = models.DateField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    total_amount = models.IntegerField(default=0)
    amount_paid = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = 'pharmacy_purchases'
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['pharmacy', 'status']),
            models.Index(fields=['supplier']),
        ]

class PharmacyPurchaseItem(SyncMixin):  # Represents individual medications in supplier purchase orders
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    purchase = models.ForeignKey(PharmacyPurchase, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT)
    quantity_ordered = models.IntegerField()
    quantity_received = models.IntegerField(default=0)
    unit_price = models.IntegerField()
    total_price = models.IntegerField()
    batch_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = 'pharmacy_purchase_items'

class PharmacySale(SyncMixin):  # Records completed pharmacy sales transactions
    PAYMENT_METHOD_CHOICES = [
        ('fedapay_mobile', 'FedaPay Mobile Money'),
        ('fedapay_card', 'FedaPay Card'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('moov_money', 'Moov Money'),
        ('orange_money', 'Orange Money'),
        ('onsite_cash', 'On-site Cash'),
        ('insurance', 'Insurance'),
        # NO WALLET - BINTACURA does not store money, all payments via external gateways
    ]

    sale_number = models.CharField(max_length=50, unique=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='sales')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='pharmacy_purchases', null=True, blank=True)
    order = models.ForeignKey(PharmacyOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    total_amount = models.IntegerField()
    discount_amount = models.IntegerField(default=0)
    tax_amount = models.IntegerField(default=0)
    final_amount = models.IntegerField()
    amount_paid = models.IntegerField()
    change_given = models.IntegerField(default=0)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    transaction_ref = models.CharField(max_length=100, blank=True)
    cashier = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, related_name='pharmacy_sales_handled')
    sale_date = models.DateTimeField(default=timezone.now)

    class Meta:  # Meta class implementation
        db_table = 'pharmacy_sales'
        ordering = ['-sale_date']
        indexes = [
            models.Index(fields=['pharmacy', 'sale_date']),
            models.Index(fields=['sale_number']),
        ]

class PharmacySaleItem(SyncMixin):  # Represents individual medications in pharmacy sales
    sale = models.ForeignKey(PharmacySale, on_delete=models.CASCADE, related_name='items')
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT)
    inventory_item = models.ForeignKey(PharmacyInventory, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField()
    unit_price = models.IntegerField()
    total_price = models.IntegerField()

    class Meta:  # Meta class implementation
        db_table = 'pharmacy_sale_items'

class PharmacyStaff(SyncMixin):  # Manages pharmacy staff members and their access permissions
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('pharmacist', 'Pharmacist'),
        ('cashier', 'Cashier'),
        ('inventory_clerk', 'Inventory Clerk'),
        ('delivery_person', 'Delivery Person'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='pharmacy_staff_members')
    staff_participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='pharmacy_staff_profile', null=True, blank=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    hire_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    can_manage_inventory = models.BooleanField(default=False)
    can_process_orders = models.BooleanField(default=False)
    can_handle_sales = models.BooleanField(default=False)
    can_manage_staff = models.BooleanField(default=False)

    class Meta:  # Meta class implementation
        db_table = 'pharmacy_staff'
        indexes = [
            models.Index(fields=['pharmacy', 'is_active']),
            models.Index(fields=['email']),
        ]

class DoctorPharmacyReferral(SyncMixin):  # Tracks doctor prescription referrals to pharmacies for bonus programs
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    doctor = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='pharmacy_referrals')
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='doctor_referrals')
    prescription = models.ForeignKey('prescriptions.Prescription', on_delete=models.CASCADE, related_name='pharmacy_referrals')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='received_referrals')
    referral_date = models.DateTimeField(default=timezone.now)
    was_fulfilled = models.BooleanField(default=False)
    fulfillment_date = models.DateTimeField(null=True, blank=True)
    total_amount = models.IntegerField(default=0)
    bonus_earned = models.IntegerField(default=0)
    bonus_paid = models.BooleanField(default=False)
    bonus_paid_date = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = 'doctor_pharmacy_referrals'
        indexes = [
            models.Index(fields=['doctor', 'pharmacy']),
            models.Index(fields=['referral_date']),
            models.Index(fields=['was_fulfilled']),
            models.Index(fields=['bonus_paid']),
        ]

class PharmacyBonusConfig(SyncMixin):  # Configures referral bonus programs between pharmacies and doctors
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='bonus_configs')
    doctor = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='pharmacy_bonus_configs', null=True, blank=True)
    bonus_type = models.CharField(max_length=30, choices=[
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
        ('tiered', 'Tiered'),
    ], default='percentage')
    bonus_percentage = models.IntegerField(default=0, help_text="Bonus percentage in basis points (e.g., 500 = 5%)")
    fixed_bonus_amount = models.IntegerField(default=0, help_text="Fixed bonus amount in XOF cents")
    min_prescriptions_per_month = models.IntegerField(default=0)
    max_prescriptions_per_month = models.IntegerField(default=0)
    bonus_amount_for_tier = models.IntegerField(default=0, help_text="Tier bonus amount in XOF cents")
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(default=timezone.now)
    valid_until = models.DateField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = 'pharmacy_bonus_configs'
        indexes = [
            models.Index(fields=['pharmacy', 'is_active']),
            models.Index(fields=['doctor']),
        ]

class PharmacyStockMovement(SyncMixin):  # Records all inventory movements including sales, purchases, and adjustments
    MOVEMENT_TYPE_CHOICES = [
        ('in', 'Entrée'),
        ('out', 'Sortie'),
        ('adjustment', 'Ajustement'),
        ('return', 'Retour'),
        ('transfer', 'Transfert'),
        ('expired', 'Périmé'),
        ('damaged', 'Endommagé'),
    ]

    REASON_CHOICES = [
        ('purchase', 'Réapprovisionnement'),
        ('sale', 'Vente'),
        ('correction', 'Correction d\'inventaire'),
        ('return_supplier', 'Retour fournisseur'),
        ('return_customer', 'Retour client'),
        ('transfer_in', 'Transfert entrant'),
        ('transfer_out', 'Transfert sortant'),
        ('expired', 'Produit expiré'),
        ('damaged', 'Produit endommagé'),
        ('theft', 'Vol'),
        ('loss', 'Perte'),
        ('donation', 'Don'),
        ('sample', 'Échantillon'),
        ('other', 'Autre'),
    ]

    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='stock_movements')
    inventory_item = models.ForeignKey(PharmacyInventory, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    quantity = models.IntegerField()
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    previous_quantity = models.IntegerField()
    new_quantity = models.IntegerField()
    performed_by = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, related_name='performed_movements')
    movement_date = models.DateTimeField(default=timezone.now)

    class Meta:  # Meta class implementation
        db_table = 'pharmacy_stock_movements'
        ordering = ['-movement_date']
        indexes = [
            models.Index(fields=['pharmacy', 'movement_date']),
            models.Index(fields=['inventory_item']),
            models.Index(fields=['movement_type']),
        ]


# ========================================
# INVENTORY MANAGEMENT IMPROVEMENTS
# ========================================

class ExpiryAlert(SyncMixin):  # Tracks expiry date alerts for medications approaching expiration
    """
    ISSUE-PHR-018: NO expiry date alerts
    Proactively alerts pharmacies about medications expiring soon
    """
    ALERT_TYPE_CHOICES = [
        ('30_days', '30 Days Before Expiry'),
        ('60_days', '60 Days Before Expiry'),
        ('90_days', '90 Days Before Expiry'),
        ('expired', 'Already Expired'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('ignored', 'Ignored'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='expiry_alerts')
    inventory_item = models.ForeignKey(PharmacyInventory, on_delete=models.CASCADE, related_name='expiry_alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    expiry_date = models.DateField()
    days_until_expiry = models.IntegerField()
    quantity_affected = models.IntegerField()
    estimated_loss_value = models.IntegerField(default=0, help_text="Potential financial loss if not sold in XOF cents")

    alert_date = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_expiry_alerts'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)

    class Meta:
        db_table = 'expiry_alerts'
        ordering = ['-alert_date']
        indexes = [
            models.Index(fields=['pharmacy', 'status']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['alert_type']),
        ]

    def __str__(self):
        return f"{self.alert_type} - {self.inventory_item.medication.name} (Expires: {self.expiry_date})"


class StockReconciliation(SyncMixin):  # Manages physical inventory counts and reconciliation
    """
    ISSUE-PHR-019: NO stock reconciliation system
    Allows pharmacies to perform physical counts and reconcile with system
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='reconciliations')
    reconciliation_number = models.CharField(max_length=50, unique=True)
    reconciliation_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    initiated_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiated_reconciliations'
    )
    completed_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_reconciliations'
    )

    total_items_counted = models.IntegerField(default=0)
    items_with_discrepancies = models.IntegerField(default=0)
    total_variance_value = models.IntegerField(default=0, help_text="Total variance value in XOF cents")

    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'stock_reconciliations'
        ordering = ['-reconciliation_date']
        indexes = [
            models.Index(fields=['pharmacy', 'status']),
            models.Index(fields=['reconciliation_date']),
        ]

    def __str__(self):
        return f"Reconciliation {self.reconciliation_number} - {self.reconciliation_date}"


class StockReconciliationItem(SyncMixin):  # Records individual item counts during reconciliation
    """Line items for stock reconciliation showing system vs actual counts"""

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    reconciliation = models.ForeignKey(StockReconciliation, on_delete=models.CASCADE, related_name='items')
    inventory_item = models.ForeignKey(PharmacyInventory, on_delete=models.CASCADE, related_name='reconciliation_items')

    system_quantity = models.IntegerField(help_text="Quantity according to system")
    counted_quantity = models.IntegerField(help_text="Actual physical count")
    variance = models.IntegerField(help_text="Difference (counted - system)")
    variance_percentage = models.IntegerField(default=0, help_text="Variance percentage in basis points (e.g., 1000 = 10%)")

    unit_price = models.IntegerField(help_text="Unit price in XOF cents")
    variance_value = models.IntegerField(help_text="Financial impact of variance in XOF cents")

    reason = models.CharField(
        max_length=50,
        choices=[
            ('theft', 'Theft/Loss'),
            ('damage', 'Damaged'),
            ('expired', 'Expired'),
            ('miscounted', 'Previous Miscount'),
            ('unreported_sale', 'Unreported Sale'),
            ('unreported_purchase', 'Unreported Purchase'),
            ('other', 'Other'),
        ],
        blank=True
    )
    notes = models.TextField(blank=True)
    counted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'stock_reconciliation_items'
        indexes = [
            models.Index(fields=['reconciliation', 'inventory_item']),
        ]

    def save(self, *args, **kwargs):
        """Auto-calculate variance and variance value"""
        self.variance = self.counted_quantity - self.system_quantity
        if self.system_quantity > 0:
            self.variance_percentage = int((self.variance / self.system_quantity) * 10000)  # Convert to basis points
        self.variance_value = self.variance * self.unit_price
        super().save(*args, **kwargs)


# ========================================
# CASH REGISTER & END-OF-DAY MANAGEMENT
# ========================================

class CashRegister(SyncMixin):  # Manages cash register for pharmacy sales
    """
    ISSUE-PHR-047: NO cash register management
    Tracks opening balance, cash movements, and closing balance
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('reconciled', 'Reconciled'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='cash_registers')
    register_number = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    opened_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        related_name='opened_registers'
    )
    closed_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_registers'
    )

    opening_balance = models.IntegerField(default=0, help_text="Opening balance in XOF cents")
    expected_closing_balance = models.IntegerField(default=0, help_text="Expected closing balance in XOF cents")
    actual_closing_balance = models.IntegerField(default=0, null=True, blank=True, help_text="Actual closing balance in XOF cents")
    variance = models.IntegerField(default=0, help_text="Variance in XOF cents")

    total_cash_sales = models.IntegerField(default=0, help_text="Total cash sales in XOF cents")
    total_card_sales = models.IntegerField(default=0, help_text="Total card sales in XOF cents")
    total_mobile_money_sales = models.IntegerField(default=0, help_text="Total mobile money sales in XOF cents")
    total_insurance_sales = models.IntegerField(default=0, help_text="Total insurance sales in XOF cents")

    number_of_transactions = models.IntegerField(default=0)

    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    reconciled_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'cash_registers'
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['pharmacy', 'status']),
            models.Index(fields=['opened_at']),
        ]

    def __str__(self):
        return f"Register {self.register_number} - {self.opened_at.date()}"


class EndOfDaySettlement(SyncMixin):  # Manages end-of-day settlement process
    """
    ISSUE-PHR-048: NO end-of-day settlement process
    Comprehensive EOD reconciliation and reporting
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
        ('disputed', 'Disputed'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='eod_settlements')
    settlement_number = models.CharField(max_length=50, unique=True)
    settlement_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='eod_settlements'
    )

    # Sales Summary (all in XOF cents)
    total_revenue = models.IntegerField(default=0, help_text="Total revenue in XOF cents")
    total_cost_of_goods = models.IntegerField(default=0, help_text="Total COGS in XOF cents")
    gross_profit = models.IntegerField(default=0, help_text="Gross profit in XOF cents")

    cash_sales = models.IntegerField(default=0, help_text="Cash sales in XOF cents")
    card_sales = models.IntegerField(default=0, help_text="Card sales in XOF cents")
    mobile_money_sales = models.IntegerField(default=0, help_text="Mobile money sales in XOF cents")
    insurance_claims = models.IntegerField(default=0, help_text="Insurance claims in XOF cents")

    # Transaction Counts
    total_transactions = models.IntegerField(default=0)
    total_items_sold = models.IntegerField(default=0)
    prescriptions_filled = models.IntegerField(default=0)
    otc_sales = models.IntegerField(default=0)

    # Cash Management (all in XOF cents)
    opening_cash = models.IntegerField(default=0, help_text="Opening cash in XOF cents")
    closing_cash = models.IntegerField(default=0, help_text="Closing cash in XOF cents")
    cash_variance = models.IntegerField(default=0, help_text="Cash variance in XOF cents")

    # Staff
    prepared_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prepared_settlements'
    )
    approved_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_settlements'
    )

    notes = models.TextField(blank=True)
    discrepancies = models.TextField(blank=True, help_text="Note any discrepancies found")

    prepared_at = models.DateTimeField(default=timezone.now)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'eod_settlements'
        ordering = ['-settlement_date']
        indexes = [
            models.Index(fields=['pharmacy', 'settlement_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"EOD {self.settlement_number} - {self.settlement_date}"

    def save(self, *args, **kwargs):
        """Auto-calculate gross profit and cash variance"""
        self.gross_profit = self.total_revenue - self.total_cost_of_goods
        self.cash_variance = self.closing_cash - (self.opening_cash + self.cash_sales)
        super().save(*args, **kwargs)


# ========================================
# MULTI-COUNTER WORKFLOW MANAGEMENT
# ========================================

class PharmacyCounter(SyncMixin):
    """
    Physical counter/terminal in pharmacy
    Multiple staff can work at different counters simultaneously
    """
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='counters')
    counter_number = models.CharField(max_length=50)
    counter_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    current_staff = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_counter'
    )
    current_session_started = models.DateTimeField(null=True, blank=True)
    
    cash_register = models.ForeignKey(
        CashRegister,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='counter'
    )
    
    class Meta:
        db_table = 'pharmacy_counters'
        unique_together = ['pharmacy', 'counter_number']
        indexes = [
            models.Index(fields=['pharmacy', 'is_active']),
        ]

    def __str__(self):
        return f"{self.pharmacy.full_name} - Counter {self.counter_number}"


class OrderQueue(SyncMixin):
    """
    Queue system for prescription orders
    Any staff at any counter can see and claim orders
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('claimed', 'Claimed by Staff'),
        ('preparing', 'Preparing Medications'),
        ('ready', 'Ready for Pickup/Delivery'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='order_queues')
    order = models.OneToOneField(PharmacyOrder, on_delete=models.CASCADE, related_name='queue_status')
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    queue_number = models.IntegerField()
    priority = models.IntegerField(default=0, help_text="Higher priority processed first")
    
    claimed_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claimed_orders'
    )
    claimed_at = models.DateTimeField(null=True, blank=True)
    
    counter = models.ForeignKey(
        PharmacyCounter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_orders'
    )
    
    estimated_ready_time = models.DateTimeField(null=True, blank=True)
    actual_ready_time = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    qr_code = models.CharField(max_length=100, unique=True, help_text="QR code for pickup verification")
    
    class Meta:
        db_table = 'order_queue'
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['pharmacy', 'status']),
            models.Index(fields=['queue_number']),
            models.Index(fields=['qr_code']),
        ]

    def __str__(self):
        return f"Queue #{self.queue_number} - Order {self.order.order_number}"


class DeliveryTracking(SyncMixin):
    """
    Track delivery status for pharmacy orders with patient confirmation
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Assignment'),
        ('assigned', 'Assigned to Delivery Person'),
        ('picked_up', 'Picked Up from Pharmacy'),
        ('in_transit', 'In Transit'),
        ('arrived', 'Arrived at Destination'),
        ('delivered', 'Delivered & Confirmed'),
        ('failed', 'Delivery Failed'),
        ('returned', 'Returned to Pharmacy'),
    ]
    
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='deliveries')
    order = models.OneToOneField(PharmacyOrder, on_delete=models.CASCADE, related_name='delivery_tracking')
    
    tracking_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    
    delivery_person = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deliveries_assigned'
    )
    
    delivery_address = models.TextField()
    delivery_phone = models.CharField(max_length=20)
    delivery_instructions = models.TextField(blank=True)
    
    assigned_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    patient_confirmation_code = models.CharField(max_length=10, help_text="Code patient provides to confirm delivery")
    confirmed_by_patient = models.BooleanField(default=False)
    confirmation_time = models.DateTimeField(null=True, blank=True)
    
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    
    delivery_notes = models.TextField(blank=True)
    failed_reason = models.TextField(blank=True)
    delivery_photo = models.ImageField(upload_to='delivery_photos/', null=True, blank=True)
    
    class Meta:
        db_table = 'delivery_tracking'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pharmacy', 'status']),
            models.Index(fields=['tracking_number']),
            models.Index(fields=['delivery_person', 'status']),
        ]

    def __str__(self):
        return f"Delivery {self.tracking_number} - {self.order.order_number}"


class PickupVerification(SyncMixin):
    """
    Records for on-site pickup verification using QR codes
    """
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    pharmacy = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='pickup_verifications')
    order = models.OneToOneField(PharmacyOrder, on_delete=models.CASCADE, related_name='pickup_verification')
    
    qr_code = models.CharField(max_length=100, unique=True)
    verification_code = models.CharField(max_length=10, help_text="Backup verification code")
    
    scanned_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        related_name='verified_pickups'
    )
    scanned_at = models.DateTimeField(null=True, blank=True)
    
    counter = models.ForeignKey(
        PharmacyCounter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pickup_verifications'
    )
    
    payment_completed = models.BooleanField(default=False)
    payment_transaction_ref = models.CharField(max_length=100, blank=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'pickup_verifications'
        indexes = [
            models.Index(fields=['pharmacy', 'scanned_at']),
            models.Index(fields=['qr_code']),
        ]

    def __str__(self):
        return f"Pickup {self.order.order_number} - QR: {self.qr_code}"

