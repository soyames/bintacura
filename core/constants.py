"""
Central constants file for BintaCura platform.
Ensures consistency across all models and prevents choice list divergence.
"""

# Payment Method Choices - Used across appointments, payments, transactions
PAYMENT_METHOD_CHOICES = [
    ('cash', 'Cash'),
    ('onsite_cash', 'On-site Cash'),
    ('card', 'Card'),
    ('mobile_money', 'Mobile Money'),
    ('insurance', 'Insurance'),
    ('wallet', 'Wallet'),
]

# Currency Choices - Supported currencies on the platform
CURRENCY_CHOICES = [
    ('XOF', 'West African CFA Franc'),
    ('XAF', 'Central African CFA Franc'),
    ('USD', 'US Dollar'),
    ('EUR', 'Euro'),
    ('GBP', 'British Pound'),
    ('NGN', 'Nigerian Naira'),
    ('GHS', 'Ghanaian Cedi'),
    ('KES', 'Kenyan Shilling'),
    ('ZAR', 'South African Rand'),
    ('MAD', 'Moroccan Dirham'),
    ('TND', 'Tunisian Dinar'),
    ('EGP', 'Egyptian Pound'),
]

# Platform base currency
BASE_CURRENCY = 'XOF'

# Transaction Status Choices
TRANSACTION_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
    ('refunded', 'Refunded'),
]

# Appointment Status Choices
APPOINTMENT_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
    ('rejected', 'Rejected'),
    ('in_progress', 'In Progress'),
    ('no_show', 'No Show'),
]

# Payment Status Choices
PAYMENT_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('paid', 'Paid'),
    ('refunded', 'Refunded'),
    ('failed', 'Failed'),
]

# Participant Roles
PARTICIPANT_ROLES = [
    ('patient', 'Patient'),
    ('doctor', 'Doctor'),
    ('hospital', 'Hospital'),
    ('pharmacy', 'Pharmacy'),
    ('insurance', 'Insurance Company'),
    ('admin', 'Admin'),
]

# Service Types
SERVICE_TYPE_CHOICES = [
    ('consultation', 'Consultation'),
    ('telemedicine', 'Telemedicine'),
    ('prescription', 'Prescription'),
    ('pharmacy_service', 'Pharmacy Service'),
    ('insurance_claim', 'Insurance Claim'),
    ('hospital_service', 'Hospital Service'),
    ('emergency', 'Emergency Service'),
    ('surgery', 'Surgery'),
    ('diagnostic', 'Diagnostic Service'),
    ('other', 'Other'),
]

# Prescription Status
PRESCRIPTION_STATUS_CHOICES = [
    ('active', 'Active'),
    ('expired', 'Expired'),
    ('pendingRenewal', 'Pending Renewal'),
    ('renewed', 'Renewed'),
    ('used', 'Used'),
    ('cancelled', 'Cancelled'),
    ('rejected', 'Rejected'),
    ('ordered', 'Ordered'),
    ('fulfilled', 'Fulfilled'),
    ('partiallyFulfilled', 'Partially Fulfilled'),
    ('verified', 'Verified'),
    ('transferred', 'Transferred'),
    ('suspended', 'Suspended'),
]

# Insurance Claim Status
INSURANCE_CLAIM_STATUS_CHOICES = [
    ('submitted', 'Submitted'),
    ('underReview', 'Under Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('paid', 'Paid'),
]

# Gender Choices
GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
]

# Blood Type Choices
BLOOD_TYPE_CHOICES = [
    ('A+', 'A Positive'),
    ('A-', 'A Negative'),
    ('B+', 'B Positive'),
    ('B-', 'B Negative'),
    ('AB+', 'AB Positive'),
    ('AB-', 'AB Negative'),
    ('O+', 'O Positive'),
    ('O-', 'O Negative'),
]

# Language Choices
LANGUAGE_CHOICES = [
    ('fr', 'Français'),
    ('en', 'English'),
]

# Region Codes - Multi-region support
REGION_CHOICES = [
    ('global', 'Global'),
    ('west_africa', 'West Africa'),
    ('central_africa', 'Central Africa'),
    ('east_africa', 'East Africa'),
    ('north_africa', 'North Africa'),
    ('southern_africa', 'Southern Africa'),
]
