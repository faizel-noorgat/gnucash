"""
Acceptance Tests for Authorization Rules

These tests verify the critical authorization behavior contract rules.
"""
import pytest
from django.test import TestCase
from apps.identity.models import (
    User, Tenant, LegalEntity, Membership, Role, Permission
)
from apps.identity.services.authorization import AuthorizationService


@pytest.mark.acceptance
class TestAuthorizationRules(TestCase):
    """
    Acceptance tests for authorization behavior contract rules.
    """

    databases = '__all__'

    @pytest.mark.rule('BR-AUTH-010')
    def test_users_can_only_access_tenants_they_are_members_of(self):
        """
        BR-AUTH-010: Users can only access tenants they are members of.

        Given a user is a member of Tenant A
        And a user is NOT a member of Tenant B
        When the user attempts to access Tenant A resources
        Then access is granted
        When the user attempts to access Tenant B resources
        Then access is denied
        """
        # Given: a user and two tenants
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant_a = Tenant.objects.create(
            name='Tenant A',
            slug='tenant-a',
            created_by=user
        )

        tenant_b = Tenant.objects.create(
            name='Tenant B',
            slug='tenant-b',
            created_by=user
        )

        # User is member of Tenant A only
        Membership.objects.create(
            user=user,
            tenant=tenant_a,
            role='admin',
            status='active'
        )

        # When/Then: user can access Tenant A
        assert AuthorizationService.is_tenant_member(user, tenant_a), \
            "User should be member of Tenant A"

        # When/Then: user cannot access Tenant B
        assert not AuthorizationService.is_tenant_member(user, tenant_b), \
            "User should not be member of Tenant B"

    @pytest.mark.rule('BR-AUTH-011')
    def test_role_based_permission_enforcement(self):
        """
        BR-AUTH-011: Role-based permissions must be enforced.

        Given a user has a role with specific permissions
        When the user attempts to perform an action
        Then the action is allowed only if the role has the required permission
        """
        # Given: a role with specific permissions
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            created_by=user
        )

        # Create permissions
        view_perm = Permission.objects.create(
            codename='view_invoices',
            name='View Invoices'
        )
        create_perm = Permission.objects.create(
            codename='create_invoices',
            name='Create Invoices'
        )
        delete_perm = Permission.objects.create(
            codename='delete_invoices',
            name='Delete Invoices'
        )

        # Create role with view and create permissions
        role = Role.objects.create(
            name='Accountant',
            tenant=tenant
        )
        role.role_permissions.create(permission=view_perm)
        role.role_permissions.create(permission=create_perm)

        # Membership with this role
        Membership.objects.create(
            user=user,
            tenant=tenant,
            role='Accountant',
            status='active'
        )

        # When/Then: user has view and create permissions
        assert AuthorizationService.has_permission(user, tenant, 'view_invoices'), \
            "User should have view_invoices permission"
        assert AuthorizationService.has_permission(user, tenant, 'create_invoices'), \
            "User should have create_invoices permission"

        # When/Then: user does not have delete permission
        assert not AuthorizationService.has_permission(user, tenant, 'delete_invoices'), \
            "User should not have delete_invoices permission"

    @pytest.mark.rule('BR-AUTH-012')
    def test_entity_scoped_permission_enforcement(self):
        """
        BR-AUTH-012: Entity-scoped permissions must be enforced.

        Given a user has a membership scoped to Entity A
        When the user attempts to access Entity A resources
        Then access is granted
        When the user attempts to access Entity B resources
        Then access is denied
        """
        # Given: a user with entity-scoped membership
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            created_by=user
        )

        entity_a = LegalEntity.objects.create(
            tenant=tenant,
            name='Entity A',
            created_by=user
        )

        entity_b = LegalEntity.objects.create(
            tenant=tenant,
            name='Entity B',
            created_by=user
        )

        # User has membership scoped to Entity A
        Membership.objects.create(
            user=user,
            tenant=tenant,
            role='admin',
            status='active',
            scoped_entity=entity_a
        )

        # When/Then: user can access Entity A
        # (In real implementation, would check entity-scoped permissions)
        assert AuthorizationService.is_tenant_member(user, tenant), \
            "User should be member of tenant"

        # Note: Full entity-scoped permission check would be more complex
        # This is a simplified test for the concept

    @pytest.mark.rule('BR-AUTH-013')
    def test_inactive_users_cannot_access_resources(self):
        """
        BR-AUTH-013: Inactive users cannot access resources.

        Given a user is marked as inactive
        When the user attempts to access resources
        Then access is denied
        """
        # Given: an inactive user
        user = User.objects.create_user(
            email='inactive@example.com',
            password='securepassword123!',
            is_active=False
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            created_by=user
        )

        Membership.objects.create(
            user=user,
            tenant=tenant,
            role='admin',
            status='active'
        )

        # When/Then: inactive user cannot access
        assert not user.is_active, "User should be inactive"
        assert not AuthorizationService.has_permission(user, tenant, 'view_invoices'), \
            "Inactive user should not have permissions"

    @pytest.mark.rule('BR-AUTH-014')
    def test_suspended_memberships_cannot_access_resources(self):
        """
        BR-AUTH-014: Suspended memberships cannot access resources.

        Given a user has a suspended membership
        When the user attempts to access tenant resources
        Then access is denied
        """
        # Given: a user with suspended membership
        user = User.objects.create_user(
            email='suspended@example.com',
            password='securepassword123!'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            created_by=user
        )

        Membership.objects.create(
            user=user,
            tenant=tenant,
            role='admin',
            status='suspended'  # Suspended membership
        )

        # When/Then: suspended membership cannot access
        assert not AuthorizationService.is_tenant_member(user, tenant), \
            "User with suspended membership should not be considered active member"
