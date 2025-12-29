import random
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from payments.models import ParticipantPhone

logger = logging.getLogger(__name__)


class PhoneVerificationService:  # Service class for PhoneVerification operations

    @staticmethod
    def generate_verification_code():  # Generate verification code
        return str(random.randint(100000, 999999))

    @staticmethod
    def initiate_phone_verification(participant, phone_number, country_code, is_primary=False):  # Initiate phone verification
        phone, created = ParticipantPhone.objects.get_or_create(
            participant=participant,
            phone_number=phone_number,
            defaults={
                'country_code': country_code,
                'is_primary': is_primary,
            }
        )

        if not created:
            phone.country_code = country_code
            phone.is_primary = is_primary

        verification_code = PhoneVerificationService.generate_verification_code()
        phone.verification_code = verification_code
        phone.verification_code_expires_at = timezone.now() + timedelta(minutes=10)
        phone.is_verified = False
        phone.save()

        success = PhoneVerificationService.send_verification_sms(
            phone_number=phone_number,
            verification_code=verification_code,
            participant_name=participant.full_name or participant.email
        )

        return {
            'success': success,
            'phone_id': str(phone.id),
            'phone_number': phone_number,
            'expires_in': 600,
            'message': 'Verification code sent successfully' if success else 'Failed to send verification code'
        }

    @staticmethod
    def send_verification_sms(phone_number, verification_code, participant_name):  # Send verification sms
        try:
            message = f"BINTACURA: Your verification code is {verification_code}. Valid for 10 minutes. Do not share this code."

            if hasattr(settings, 'USE_AWS_SNS') and settings.USE_AWS_SNS:
                return PhoneVerificationService._send_via_aws_sns(phone_number, message)
            else:
                logger.info(f"SMS to {phone_number}: {message}")
                return True

        except Exception as e:
            logger.error(f"Failed to send verification SMS: {str(e)}")
            return False

    @staticmethod
    def _send_via_aws_sns(phone_number, message):  # Send via aws sns
        try:
            import boto3

            sns_client = boto3.client(
                'sns',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )

            response = sns_client.publish(
                PhoneNumber=phone_number,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': 'Transactional'
                    }
                }
            )

            logger.info(f"SMS sent successfully to {phone_number}. MessageId: {response['MessageId']}")
            return True

        except Exception as e:
            logger.error(f"AWS SNS error: {str(e)}")
            return False

    @staticmethod
    def verify_phone_code(phone_id, verification_code):  # Verify phone code
        try:
            phone = ParticipantPhone.objects.get(id=phone_id)

            if phone.is_verified:
                return {
                    'success': False,
                    'message': 'Phone number already verified'
                }

            if not phone.verification_code:
                return {
                    'success': False,
                    'message': 'No verification code found. Please request a new code.'
                }

            if phone.verification_code_expires_at < timezone.now():
                return {
                    'success': False,
                    'message': 'Verification code expired. Please request a new code.'
                }

            if phone.verification_code != verification_code:
                return {
                    'success': False,
                    'message': 'Invalid verification code'
                }

            phone.is_verified = True
            phone.verified_at = timezone.now()
            phone.verification_code = ''
            phone.verification_code_expires_at = None
            phone.save()

            if phone.is_primary:
                ParticipantPhone.objects.filter(
                    participant=phone.participant
                ).exclude(id=phone.id).update(is_primary=False)

            return {
                'success': True,
                'message': 'Phone number verified successfully',
                'phone_id': str(phone.id),
                'phone_number': phone.phone_number
            }

        except ParticipantPhone.DoesNotExist:
            return {
                'success': False,
                'message': 'Phone not found'
            }
        except Exception as e:
            logger.error(f"Phone verification error: {str(e)}")
            return {
                'success': False,
                'message': 'Verification failed. Please try again.'
            }

    @staticmethod
    def get_participant_phones(participant):  # Get participant phones
        return ParticipantPhone.objects.filter(participant=participant).order_by('-is_primary', '-created_at')

    @staticmethod
    def set_primary_phone(participant, phone_id):  # Set primary phone
        try:
            phone = ParticipantPhone.objects.get(id=phone_id, participant=participant)

            if not phone.is_verified:
                return {
                    'success': False,
                    'message': 'Cannot set unverified phone as primary'
                }

            ParticipantPhone.objects.filter(participant=participant).update(is_primary=False)

            phone.is_primary = True
            phone.save()

            return {
                'success': True,
                'message': 'Primary phone updated successfully'
            }

        except ParticipantPhone.DoesNotExist:
            return {
                'success': False,
                'message': 'Phone not found'
            }

