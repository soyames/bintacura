from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.conf import settings

from .preferences import ParticipantPreferences, EmergencyContact
from .preferences_serializers import (
    ParticipantPreferencesSerializer,
    EmergencyContactSerializer
)


class LanguagePreferenceView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'preferred_language': request.user.preferred_language,
            'supported_languages': [{'code': code, 'name': name} for code, name in settings.LANGUAGES]
        })
    
    def post(self, request):
        language_code = request.data.get('language')
        if not language_code:
            return Response({'error': 'Language code is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        supported_languages = dict(settings.LANGUAGES)
        if language_code not in supported_languages:
            return Response({
                'error': f'Language "{language_code}" is not supported',
                'supported_languages': list(supported_languages.keys())
            }, status=status.HTTP_400_BAD_REQUEST)
        
        request.user.preferred_language = language_code
        request.user.save(update_fields=['preferred_language'])
        
        return Response({
            'status': 'success',
            'preferred_language': language_code,
            'language_name': supported_languages[language_code]
        })


class ParticipantPreferencesView(APIView):
    """
    API view for managing participant preferences.
    GET: Retrieve current preferences
    PUT/PATCH: Update preferences
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get participant's current preferences."""
        preferences, created = ParticipantPreferences.objects.get_or_create(
            participant=request.user
        )
        serializer = ParticipantPreferencesSerializer(preferences)
        return Response(serializer.data)
    
    def put(self, request):
        """Update participant's preferences (full update)."""
        preferences, created = ParticipantPreferences.objects.get_or_create(
            participant=request.user
        )
        serializer = ParticipantPreferencesSerializer(
            preferences,
            data=request.data,
            partial=False
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """Update participant's preferences (partial update)."""
        preferences, created = ParticipantPreferences.objects.get_or_create(
            participant=request.user
        )
        serializer = ParticipantPreferencesSerializer(
            preferences,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmergencyContactListView(APIView):
    """
    API view for managing emergency contacts.
    GET: List all emergency contacts
    POST: Create new emergency contact
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all emergency contacts for participant."""
        contacts = EmergencyContact.objects.filter(participant=request.user)
        serializer = EmergencyContactSerializer(contacts, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Create new emergency contact."""
        serializer = EmergencyContactSerializer(
            data=request.data,
            context={'participant': request.user}
        )
        if serializer.is_valid():
            serializer.save(participant=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmergencyContactDetailView(APIView):
    """
    API view for managing individual emergency contact.
    GET: Retrieve contact details
    PUT/PATCH: Update contact
    DELETE: Remove contact
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        """Get emergency contact ensuring it belongs to the user."""
        return get_object_or_404(
            EmergencyContact,
            pk=pk,
            participant=user
        )
    
    def get(self, request, pk):
        """Get emergency contact details."""
        contact = self.get_object(pk, request.user)
        serializer = EmergencyContactSerializer(contact)
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update emergency contact (full update)."""
        contact = self.get_object(pk, request.user)
        serializer = EmergencyContactSerializer(
            contact,
            data=request.data,
            context={'participant': request.user}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """Update emergency contact (partial update)."""
        contact = self.get_object(pk, request.user)
        serializer = EmergencyContactSerializer(
            contact,
            data=request.data,
            partial=True,
            context={'participant': request.user}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Delete emergency contact."""
        contact = self.get_object(pk, request.user)
        contact.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
