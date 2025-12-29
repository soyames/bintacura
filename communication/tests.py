from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from core.models import Participant
from .models import CommunityProfile, CommunityPost


class CommunityProfileModelTest(TestCase):  # CommunityProfileModelTest class implementation
    def setUp(self):  # Setup
        self.user = Participant.objects.create_user(
            email="user@test.com", password="test123", role="patient"
        )

    def test_create_community_profile(self):  # Test create community profile
        profile = CommunityProfile.objects.create(
            participant=self.user,
            handle="testuser",
            display_name="Test User",
            bio="Test bio",
        )
        self.assertEqual(profile.handle, "testuser")
        self.assertFalse(profile.is_verified)
        self.assertEqual(profile.followers_count, 0)


class CommunityPostModelTest(TestCase):  # CommunityPostModelTest class implementation
    def setUp(self):  # Setup
        self.user = Participant.objects.create_user(
            email="user@test.com", password="test123", role="patient"
        )

    def test_create_post(self):  # Test create post
        post = CommunityPost.objects.create(
            author=self.user,
            author_handle="testuser",
            content="Test post content",
            post_type="text",
        )
        self.assertEqual(post.content, "Test post content")
        self.assertEqual(post.likes_count, 0)
        self.assertEqual(post.visibility, "public")
