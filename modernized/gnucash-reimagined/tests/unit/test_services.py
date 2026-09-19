"""
Unit Tests for Domain Services
"""
import pytest
from django.test import TestCase
from identity_access.domain.models import (
    User, Tenant, LegalEntity, Membership, Role, Permission, Practice
)
from identity_access.domain.services import (
    AuthenticationService, AuthorizationService, TenantService,
    MembershipService, PracticeService, NotificationService
)


class TestAuthenticationService(TestCase):
    """Unit tests for AuthenticationService."""

    def test_authenticate_user_success(self):
        """Test successful user authentication."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        authenticated_user = AuthenticationService.authenticate_user(
            'test@example.com',
            'securepassword123!'
        )

        assert authenticated_user == user

    def test_authenticate_user_failure(self):
        """Test failed user authentication."""
        User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        authenticated_user = AuthenticationService.authenticate_user(
            'test@example.com',
            'wrongpassword'
        )

        assert authenticated_user is None

    def test_generate_access_token(self):
        """Test generating access token."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        token = AuthenticationService.generate_access_token(user)

        assert token is not None
        assert isinstance(token, str)

    def test_validate_token_success(self):
        """Test successful token validation."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        token = AuthenticationService.generate_access_token(user)
        validated_user = AuthenticationService.validate_token(token)

        assert validated_user == user

    def test_validate_token_failure(self):
        """Test failed token validation."""
        validated_user = AuthenticationService.validate_token('invalid_token')

        assert validated_user is None


class TestAuthorizationService(TestCase):
    """Unit tests for AuthorizationService."""

    def test_is_tenant_member(self):
        """Test checking tenant membership."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        Membership.objects.create(
            user=user,
            tenant=tenant,
            role='admin',
            status='active'
        )

        assert AuthorizationService.is_tenant_member(user, tenant)

    def test_is_not_tenant_member(self):
        """Test checking non-membership."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        assert not AuthorizationService.is_tenant_member(user, tenant)

    def test_get_accessible_tenants(self):
        """Test getting accessible tenants."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant_a = Tenant.objects.create(
            name='Tenant A',
            slug='tenant-a'
        )

        tenant_b = Tenant.objects.create(
            name='Tenant B',
            slug='tenant-b'
        )

        Membership.objects.create(
            user=user,
            tenant=tenant_a,
            role='admin',
            status='active'
        )

        accessible_tenants = AuthorizationService.get_accessible_tenants(user)

        assert tenant_a in accessible_tenants
        assert tenant_b not in accessible_tenants


class TestTenantService(TestCase):
    """Unit tests for TenantService."""

    def test_create_tenant(self):
        """Test creating a tenant."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant = TenantService.create_tenant(
            name='Test Tenant',
            slug='test-tenant',
            created_by=user
        )

        assert tenant.name == 'Test Tenant'
        assert tenant.slug == 'test-tenant'

        # Check default legal entity was created
        assert LegalEntity.objects.filter(tenant=tenant).exists()

        # Check user was added as owner
        assert Membership.objects.filter(
            user=user,
            tenant=tenant,
            role='owner'
        ).exists()

    def test_get_tenant(self):
        """Test getting a tenant by slug."""
        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        retrieved_tenant = TenantService.get_tenant('test-tenant')

        assert retrieved_tenant == tenant

    def test_get_tenant_not_found(self):
        """Test getting a non-existent tenant."""
        retrieved_tenant = TenantService.get_tenant('non-existent')

        assert retrieved_tenant is None


class TestMembershipService(TestCase):
    """Unit tests for MembershipService."""

    def test_get_tenant_members(self):
        """Test getting tenant members."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        Membership.objects.create(
            user=user,
            tenant=tenant,
            role='admin',
            status='active'
        )

        members = MembershipService.get_tenant_members(tenant)

        assert user in [m.user for m in members]

    def test_get_user_memberships(self):
        """Test getting user memberships."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        Membership.objects.create(
            user=user,
            tenant=tenant,
            role='admin',
            status='active'
        )

        memberships = MembershipService.get_user_memberships(user)

        assert tenant in [m.tenant for m in memberships]


class TestPracticeService(TestCase):
    """Unit tests for PracticeService."""

    def test_create_practice(self):
        """Test creating a practice."""
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        practice = PracticeService.create_practice(
            name='Test Practice',
            slug='test-practice',
            created_by=user
        )

        assert practice.name == 'Test Practice'
        assert practice.slug == 'test-practice'

        # Check user was added as practice admin
        from identity_access.domain.models import PracticeMembership
        assert PracticeMembership.objects.filter(
            user=user,
            practice=practice,
            role='admin'
        ).exists()

    def test_get_practice_engagements(self):
        """Test getting practice engagements."""
        practice = Practice.objects.create(
            name='Test Practice',
            slug='test-practice'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )

        from identity_access.domain.models import ClientEngagement
        engagement = ClientEngagement.objects.create(
            practice=practice,
            tenant=tenant,
            status='active'
        )

        engagements = PracticeService.get_practice_engagements(practice)

        assert engagement in engagements


class TestNotificationService(TestCase):
    """Unit tests for NotificationService."""

    def test_get_unread_count(self):
        """Test getting unread notification count."""
        from identity_access.domain.models import Notification

        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        # Create unread notifications
        Notification.objects.create(
            recipient=user,
            title='Notification 1',
            message='Message 1'
        )

        Notification.objects.create(
            recipient=user,
            title='Notification 2',
            message='Message 2'
        )

        count = NotificationService.get_unread_count(user)

        assert count == 2

    def test_mark_all_as_read(self):
        """Test marking all notifications as read."""
        from identity_access.domain.models import Notification

        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        # Create unread notifications
        Notification.objects.create(
            recipient=user,
            title='Notification 1',
            message='Message 1'
        )

        Notification.objects.create(
            recipient=user,
            title='Notification 2',
            message='Message 2'
        )

        NotificationService.mark_all_as_read(user)

        count = NotificationService.get_unread_count(user)

        assert count == 0
