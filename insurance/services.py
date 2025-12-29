from django.db import transaction
from .models import *

from django.db import transaction
from .models import *


class InsurancePackageService:  # Service class for InsurancePackage operations
    @staticmethod
    def create_insurancepackage(data):  # Create insurancepackage
        return InsurancePackage.objects.create(**data)

    @staticmethod
    def get_insurancepackage(pk):  # Get insurancepackage
        try:
            return InsurancePackage.objects.get(pk=pk)
        except InsurancePackage.DoesNotExist:
            return None

    @staticmethod
    def update_insurancepackage(pk, data):  # Update insurancepackage
        obj = InsurancePackageService.get_insurancepackage(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_insurancepackage(pk):  # Delete insurancepackage
        obj = InsurancePackageService.get_insurancepackage(pk)
        if obj:
            obj.delete()
            return True
        return False


from django.db import transaction
from .models import *


class InsuranceClaimService:  # Service class for InsuranceClaim operations
    @staticmethod
    def create_insuranceclaim(data):  # Create insuranceclaim
        return InsuranceClaim.objects.create(**data)

    @staticmethod
    def get_insuranceclaim(pk):  # Get insuranceclaim
        try:
            return InsuranceClaim.objects.get(pk=pk)
        except InsuranceClaim.DoesNotExist:
            return None

    @staticmethod
    def update_insuranceclaim(pk, data):  # Update insuranceclaim
        obj = InsuranceClaimService.get_insuranceclaim(pk)
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        return obj

    @staticmethod
    def delete_insuranceclaim(pk):  # Delete insuranceclaim
        obj = InsuranceClaimService.get_insuranceclaim(pk)
        if obj:
            obj.delete()
            return True
        return False


class ClaimValidationService:  # Service class for ClaimValidation operations
    @staticmethod
    def validate_claim(claim):  # Validate claim
        errors = []
        warnings = []

        if not claim.insurance_card:
            errors.append("Insurance card is required")
            return {"is_valid": False, "errors": errors, "warnings": warnings}

        if claim.insurance_card.status != "active":
            errors.append(f"Insurance card status is {claim.insurance_card.status}")

        from datetime import date

        if claim.service_date > date.today():
            errors.append("Service date cannot be in the future")

        coverage_start = claim.insurance_card.coverage_start_date
        coverage_end = claim.insurance_card.coverage_end_date
        if claim.service_date < coverage_start or claim.service_date > coverage_end:
            errors.append("Service date is outside coverage period")

        package = claim.insurance_card.insurance_package
        if claim.claim_amount > (package.max_coverage_amount or float("inf")):
            errors.append(
                f"Claim amount exceeds maximum coverage of {package.max_coverage_amount}"
            )

        if claim.service_type == "consultation":
            if package.is_consultation_free:
                if claim.claim_amount > 0:
                    warnings.append("Consultation should be free under this package")
            elif package.consultation_discount_percentage > 0:
                expected_discount = claim.claim_amount * (
                    package.consultation_discount_percentage / 100
                )
                if abs(claim.discount_applied - expected_discount) > 1:
                    warnings.append(
                        f"Expected discount of {expected_discount}, but got {claim.discount_applied}"
                    )

        coverage_details = package.coverage_details or {}
        if claim.service_type in coverage_details:
            service_coverage = coverage_details[claim.service_type]
            if isinstance(service_coverage, dict):
                max_amount = service_coverage.get("max_amount")
                if max_amount and claim.claim_amount > max_amount:
                    errors.append(
                        f"{claim.service_type} claim exceeds package limit of {max_amount}"
                    )

        if not claim.attachments.exists():
            warnings.append("No supporting documents attached")

        required_docs = ["invoice", "medical_report"]
        attached_types = set(claim.attachments.values_list("document_type", flat=True))
        missing_docs = [doc for doc in required_docs if doc not in attached_types]
        if missing_docs:
            warnings.append(f"Missing recommended documents: {', '.join(missing_docs)}")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    @staticmethod
    def auto_approve_claim(claim):  # Auto approve claim
        validation = ClaimValidationService.validate_claim(claim)
        if not validation["is_valid"]:
            return False

        if claim.claim_amount > 50000:
            return False

        if not claim.attachments.filter(is_verified=True).exists():
            return False

        if len(validation["warnings"]) > 2:
            return False

        claim.status = "approved"
        claim.save()
        return True
