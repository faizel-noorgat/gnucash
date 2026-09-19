"""
Unit Tests for Domain Models
"""
import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.identity.models import (
    User, Tenant, LegalEntity, Membership, Role, Permission,
    ApiToken, Practice, PracticeMembership, ClientEngagement,
    AdvisorAccessGrant, Notification
)


class TestUserModel(TestCase):
    """Unit tests for User model."""

    def test_create_user(self):
        """Test creating a user."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        assert user.email == 'test@example.com'
        assert user.is_active
        assert user.check_password('securepassword123!')

    def test_user_full_name(self):
        """Test user full name property."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!',
            first_name='John',
            last_name='Doe'
        )

        assert user.full_name == 'John Doe'

    def test_user_full_name_fallback_to_email(self):
        """Test user full name falls back to email."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        assert user.full_name == 'test@example.com'


class TestTenantModel(TestCase):
    """Unit tests for Tenant model."""

    def test_create_tenant(self):
        """Test creating a tenant."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            created_by=user
        )

        assert tenant.name == 'Test Tenant'
        assert tenant.slug == 'test-tenant'
        assert tenant.is_active

    def test_tenant_str(self):
        """Test tenant string representation."""
        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        assert str(tenant) == 'Test Tenant'


class TestMembershipModel(TestCase):
    """Unit tests for Membership model."""

    def test_create_membership(self):
        """Test creating a membership."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        membership = Membership.objects.create(
            user=user,
            tenant=tenant,
            role='admin',
            status='active'
        )

        assert membership.user == user
        assert membership.tenant == tenant
        assert membership.role == 'admin'
        assert membership.is_active

    def test_accept_invitation(self):
        """Test accepting membership invitation."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        membership = Membership.objects.create(
            user=user,
            tenant=tenant,
            role='admin',
            status='invited'
        )

        membership.accept_invitation()

        assert membership.status == 'active'
        assert membership.accepted_at is not None


class TestApiTokenModel(TestCase):
    """Unit tests for ApiToken model."""

    def test_create_api_token(self):
        """Test creating an API token."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        token = ApiToken.objects.create(
            user=user,
            name='Test Token',
            permissions=['view_invoices']
        )

        assert token.user == user
        assert token.name == 'Test Token'
        assert token.token.startswith('fva_')
        assert token.token_prefix == token.token[:8]

    def test_token_expiration(self):
        """Test token expiration."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        # Create expired token
        token = ApiToken.objects.create(
            user=user,
            name='Expired Token',
            permissions=['view_invoices'],
            expires_at=timezone.now() - timedelta(days=1)
        )

        assert token.is_expired
        assert not token.is_valid

    def test_token_revocation(self):
        """Test token revocation."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        token = ApiToken.objects.create(
            user=user,
            name='Test Token',
            permissions=['view_invoices']
        )

        token.revoke(revoked_by_user=user)

        assert not token.is_active
        assert token.revoked_at is not None
        assert not token.is_valid


class TestPracticeModel(TestCase):
    """Unit tests for Practice model."""

    def test_create_practice(self):
        """Test creating a practice."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        practice = Practice.objects.create(
            name='Test Practice',
            slug='test-practice',
            created_by=user
        )

        assert practice.name == 'Test Practice'
        assert practice.slug == 'test-practice'
        assert practice.is_active


class TestClientEngagementModel(TestCase):
    """Unit tests for ClientEngagement model."""

    def test_create_engagement(self):
        """Test creating a client engagement."""
        practice = Practice.objects.create(
            name='Test Practice',
            slug='test-practice'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        engagement = ClientEngagement.objects.create(
            practice=practice,
            tenant=tenant,
            status='active'
        )

        assert engagement.practice == practice
        assert engagement.tenant == tenant
        assert engagement.is_active

    def test_activate_engagement(self):
        """Test activating an engagement."""
        practice = Practice.objects.create(
            name='Test Practice',
            slug='test-practice'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        engagement = ClientEngagement.objects.create(
            practice=practice,
            tenant=tenant,
            status='pending'
        )

        engagement.activate()

        assert engagement.status == 'active'
        assert engagement.started_at is not None

    def test_terminate_engagement(self):
        """Test terminating an engagement."""
        practice = Practice.objects.create(
            name='Test Practice',
            slug='test-practice'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        engagement = ClientEngagement.objects.create(
            practice=practice,
            tenant=tenant,
            status='active'
        )

        engagement.terminate()

        assert engagement.status == 'terminated'
        assert engagement.ended_at is not None


class TestAdvisorAccessGrantModel(TestCase):
    """Unit tests for AdvisorAccessGrant model."""

    def test_create_access_grant(self):
        """Test creating an advisor access grant."""
        practice = Practice.objects.create(
            name='Test Practice',
            slug='test-practice'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        engagement = ClientEngagement.objects.create(
            practice=practice,
            tenant=tenant,
            status='active'
        )

        practice_user = User.objects.create_user(
            email='practice@example.com',
            password='securepassword123!'
        )

        role = Role.objects.create(name='Accountant')

        grant = AdvisorAccessGrant.objects.create(
            engagement=engagement,
            practice_user=practice_user,
            tenant_role=role
        )

        assert grant.is_active
        assert not grant.is_expired

    def test_access_grant_expiration(self):
        """Test access grant expiration."""
        practice = Practice.objects.create(
            name='Test Practice',
            slug='test-practice'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        engagement = ClientEngagement.objects.create(
            practice=practice,
            tenant=tenant,
            status='active'
        )

        practice_user = User.objects.create_user(
            email='practice@example.com',
            password='securepassword123!'
        )

        role = Role.objects.create(name='Accountant')

        grant = AdvisorAccessGrant.objects.create(
            engagement=engagement,
            practice_user=practice_user,
            tenant_role=role,
            expires_at=timezone.now() - timedelta(days=1)
        )

        assert not grant.is_active
        assert grant.is_expired

    def test_revoke_access_grant(self):
        """Test revoking an access grant."""
        practice = Practice.objects.create(
            name='Test Practice',
            slug='test-practice'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        engagement = ClientEngagement.objects.create(
            practice=practice,
            tenant=tenant,
            status='active'
        )

        practice_user = User.objects.create_user(
            email='practice@example.com',
            password='securepassword123!'
        )

        role = Role.objects.create(name='Accountant')

        grant = AdvisorAccessGrant.objects.create(
            engagement=engagement,
            practice_user=practice_user,
            tenant_role=role
        )

        grant.revoke(revoked_by=practice_user, reason='Test revocation')

        assert not grant.is_active
        assert grant.revoked_at is not None
        assert grant.revocation_reason == 'Test revocation'


class TestNotificationModel(TestCase):
    """Unit tests for Notification model."""

    def test_create_notification(self):
        """Test creating a notification."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        notification = Notification.objects.create(
            recipient=user,
            notification_type='info',
            title='Test Notification',
            message='This is a test notification'
        )

        assert notification.recipient == user
        assert notification.title == 'Test Notification'
        assert not notification.is_read

    def test_mark_notification_as_read(self):
        """Test marking a notification as read."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        notification = Notification.objects.create(
            recipient=user,
            notification_type='info',
            title='Test Notification',
            message='This is a test notification'
        )

        notification.mark_as_read()

        assert notification.is_read
        assert notification.read_at is not None
