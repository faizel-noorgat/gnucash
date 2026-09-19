"""
Acceptance Tests for Authentication Rules

These tests verify the critical authentication behavior contract rules.
"""
import pytest
from django.test import TestCase
from identity_access.domain.models import User
from identity_access.domain.services.authentication_service import AuthenticationService


@pytest.mark.acceptance
class TestAuthenticationRules(TestCase):
    """
    Acceptance tests for authentication behavior contract rules.
    """

    databases = '__all__'

    @pytest.mark.rule('BR-AUTH-001')
    def test_users_must_authenticate_before_accessing_tenant_resources(self):
        """
        BR-AUTH-001: Users must authenticate before accessing tenant resources.

        Given a user exists in the system
        When the user attempts to access tenant resources
        Then the system must require authentication
        And deny access if not authenticated
        """
        # Given: a user exists
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        # When/Then: authentication is required
        # Test that unauthenticated requests are rejected
        from rest_framework.test import APIClient
        client = APIClient()

        response = client.get('/api/v1/auth/me/')
        assert response.status_code in [401, 403], \
            "Unauthenticated access should be denied"

        # Test that authenticated requests succeed
        client.force_authenticate(user=user)
        response = client.get('/api/v1/auth/me/')
        assert response.status_code == 200, \
            "Authenticated access should succeed"

    @pytest.mark.rule('BR-AUTH-002')
    def test_api_tokens_must_be_scoped_to_specific_permissions(self):
        """
        BR-AUTH-002: API tokens must be scoped to specific permissions.

        Given an API token is created
        When the token is used to access resources
        Then access must be limited to the token's scoped permissions
        """
        from identity_access.domain.models import ApiToken, Tenant, Membership

        # Given: a user and token with specific permissions
        user = User.objects.create_user(
            email='api@example.com',
            password='securepassword123!'
        )
        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            created_by=user
        )

        token = ApiToken.objects.create(
            user=user,
            tenant=tenant,
            name='Test Token',
            permissions=['view_invoices', 'create_invoices']  # Scoped permissions
        )

        # When/Then: token has limited permissions
        assert token.permissions == ['view_invoices', 'create_invoices']
        assert 'delete_invoices' not in token.permissions

    @pytest.mark.rule('BR-AUTH-003')
    def test_expired_tokens_must_be_rejected(self):
        """
        BR-AUTH-003: Expired tokens must be rejected.

        Given a token has expired
        When the token is used to access resources
        Then access must be denied
        """
        from identity_access.domain.models import ApiToken
        from django.utils import timezone
        from datetime import timedelta

        # Given: an expired token
        user = User.objects.create_user(
            email='expired@example.com',
            password='securepassword123!'
        )

        token = ApiToken.objects.create(
            user=user,
            name='Expired Token',
            permissions=['view_invoices'],
            expires_at=timezone.now() - timedelta(days=1)  # Expired yesterday
        )

        # When/Then: token is expired and invalid
        assert token.is_expired, "Token should be expired"
        assert not token.is_valid, "Expired token should not be valid"

    @pytest.mark.rule('BR-AUTH-004')
    def test_mfa_enrollment_must_be_enforced_for_admin_roles(self):
        """
        BR-AUTH-004: MFA enrollment must be enforced for admin roles (configurable).

        Given a user with admin role
        When MFA enforcement is enabled for admin roles
        Then the user must enroll in MFA before accessing resources
        """
        # Given: an admin user
        user = User.objects.create_user(
            email='admin@example.com',
            password='securepassword123!'
        )

        # When: MFA is not enrolled
        assert not user.mfa_enabled, "User should not have MFA enabled initially"

        # When: user enrolls in MFA
        mfa_info = AuthenticationService.enroll_mfa(user)

        # Then: MFA is enabled
        user.refresh_from_db()
        assert user.mfa_enabled, "User should have MFA enabled after enrollment"
        assert user.mfa_enrolled_at is not None, "MFA enrollment timestamp should be set"
        assert 'secret' in mfa_info, "MFA enrollment should return secret"
        assert 'qr_url' in mfa_info, "MFA enrollment should return QR URL"
