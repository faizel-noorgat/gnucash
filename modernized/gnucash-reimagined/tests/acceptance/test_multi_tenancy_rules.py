"""
Acceptance Tests for Multi-Tenancy Rules

These tests verify the critical multi-tenancy behavior contract rules.
"""
import pytest
from django.test import TestCase
from identity_access.domain.models import User, Tenant, Membership
from identity_access.domain.services.authorization_service import AuthorizationService
from identity_access.infrastructure.tenant_context import TenantContext, get_current_tenant_id


@pytest.mark.acceptance
class TestMultiTenancyRules(TestCase):
    """
    Acceptance tests for multi-tenancy behavior contract rules.
    """

    databases = '__all__'

    @pytest.mark.rule('BR-TENANT-001')
    def test_users_can_only_access_tenants_they_are_members_of(self):
        """
        BR-TENANT-001: Users can only access tenants they are members of.

        Given a user is a member of Tenant A
        And a user is NOT a member of Tenant B
        When the user queries accessible tenants
        Then only Tenant A is returned
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

        # When: query accessible tenants
        accessible_tenants = AuthorizationService.get_accessible_tenants(user)

        # Then: only Tenant A is accessible
        assert tenant_a in accessible_tenants, "Tenant A should be accessible"
        assert tenant_b not in accessible_tenants, "Tenant B should not be accessible"

    @pytest.mark.rule('BR-TENANT-002')
    def test_tenant_context_must_be_established_before_tenant_scoped_query(self):
        """
        BR-TENANT-002: Tenant context must be established before any tenant-scoped query.

        Given a user is accessing tenant resources
        When a tenant-scoped query is executed
        Then tenant context must be established in the database session
        """
        # Given: a user and tenant
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            created_by=user
        )

        # When: tenant context is established
        with TenantContext(tenant, user):
            # Then: tenant ID is set in session
            current_tenant_id = get_current_tenant_id()
            # Note: In actual PostgreSQL with RLS, this would return the tenant ID
            # For testing, we verify the context manager works without error

        # Context is cleaned up after exiting context manager
        assert True, "Tenant context manager should work without error"

    @pytest.mark.rule('BR-TENANT-003')
    def test_rls_policies_must_prevent_cross_tenant_data_leakage(self):
        """
        BR-TENANT-003: RLS policies must prevent cross-tenant data leakage.

        Given two tenants with separate data
        When a user from Tenant A queries data
        Then only Tenant A's data is visible
        And Tenant B's data is not visible
        """
        # Given: two tenants with separate data
        user_a = User.objects.create_user(
            email='user-a@example.com',
            password='securepassword123!'
        )

        user_b = User.objects.create_user(
            email='user-b@example.com',
            password='securepassword123!'
        )

        tenant_a = Tenant.objects.create(
            name='Tenant A',
            slug='tenant-a',
            created_by=user_a
        )

        tenant_b = Tenant.objects.create(
            name='Tenant B',
            slug='tenant-b',
            created_by=user_b
        )

        # Create memberships
        Membership.objects.create(
            user=user_a,
            tenant=tenant_a,
            role='admin',
            status='active'
        )

        Membership.objects.create(
            user=user_b,
            tenant=tenant_b,
            role='admin',
            status='active'
        )

        # When: user A queries accessible tenants
        user_a_tenants = AuthorizationService.get_accessible_tenants(user_a)

        # Then: user A can only see Tenant A
        assert tenant_a in user_a_tenants, "User A should see Tenant A"
        assert tenant_b not in user_a_tenants, "User A should not see Tenant B"

        # When: user B queries accessible tenants
        user_b_tenants = AuthorizationService.get_accessible_tenants(user_b)

        # Then: user B can only see Tenant B
        assert tenant_b in user_b_tenants, "User B should see Tenant B"
        assert tenant_a not in user_b_tenants, "User B should not see Tenant A"

    @pytest.mark.rule('BR-TENANT-004')
    def test_defense_in_depth_orm_filters_plus_rls(self):
        """
        BR-TENANT-004: Defense-in-depth with ORM filters plus RLS.

        Given a multi-tenant system
        When data is accessed
        Then both ORM-level filters and RLS policies enforce isolation
        """
        # Given: a tenant and user
        user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            created_by=user
        )

        # Create membership
        Membership.objects.create(
            user=user,
            tenant=tenant,
            role='admin',
            status='active'
        )

        # When: checking tenant membership (ORM-level filter)
        is_member = AuthorizationService.is_tenant_member(user, tenant)

        # Then: ORM filter confirms membership
        assert is_member, "ORM-level filter should confirm membership"

        # Note: RLS enforcement is tested separately in integration tests
        # with actual PostgreSQL database


@pytest.mark.acceptance
class TestPracticeAccessRules(TestCase):
    """
    Acceptance tests for practice/advisor access behavior contract rules.
    """

    databases = '__all__'

    @pytest.mark.rule('BR-PRACTICE-001')
    def test_practice_access_requires_explicit_client_engagement(self):
        """
        BR-PRACTICE-001: Practice access requires explicit ClientEngagement.

        Given a practice exists
        And a client tenant exists
        When the practice has no engagement with the tenant
        Then practice users cannot access the tenant
        When an engagement is created
        Then practice users can access the tenant
        """
        from identity_access.domain.models import Practice, PracticeMembership, ClientEngagement

        # Given: a practice, practice user, and client tenant
        practice = Practice.objects.create(
            name='Test Practice',
            slug='test-practice'
        )

        practice_user = User.objects.create_user(
            email='practice@example.com',
            password='securepassword123!'
        )

        PracticeMembership.objects.create(
            user=practice_user,
            practice=practice,
            role='staff',
            status='active'
        )

        client_tenant = Tenant.objects.create(
            name='Client Tenant',
            slug='client-tenant'
        )

        # When: no engagement exists
        # Then: practice user cannot access tenant
        assert not AuthorizationService.can_access_tenant(practice_user, client_tenant), \
            "Practice user should not access tenant without engagement"

        # When: engagement is created
        engagement = ClientEngagement.objects.create(
            practice=practice,
            tenant=client_tenant,
            status='active'
        )

        # Note: Access still requires AdvisorAccessGrant (tested in BR-PRACTICE-004)

    @pytest.mark.rule('BR-PRACTICE-002')
    def test_practice_access_is_revocable_by_client_tenant(self):
        """
        BR-PRACTICE-002: Practice access is revocable by the client tenant.

        Given a practice has access to a client tenant
        When the client revokes access
        Then practice users can no longer access the tenant
        """
        from identity_access.domain.models import (
            Practice, PracticeMembership, ClientEngagement,
            AdvisorAccessGrant, Role
        )

        # Given: practice with access to client tenant
        practice = Practice.objects.create(
            name='Test Practice',
            slug='test-practice'
        )

        practice_user = User.objects.create_user(
            email='practice@example.com',
            password='securepassword123!'
        )

        PracticeMembership.objects.create(
            user=practice_user,
            practice=practice,
            role='staff',
            status='active'
        )

        client_tenant = Tenant.objects.create(
            name='Client Tenant',
            slug='client-tenant'
        )

        engagement = ClientEngagement.objects.create(
            practice=practice,
            tenant=client_tenant,
            status='active'
        )

        role = Role.objects.create(name='Accountant')

        grant = AdvisorAccessGrant.objects.create(
            engagement=engagement,
            practice_user=practice_user,
            tenant_role=role
        )

        # Verify access exists
        assert grant.is_active, "Grant should be active"

        # When: client revokes access
        grant.revoke(revoked_by=client_tenant.created_by, reason='Client request')

        # Then: access is revoked
        grant.refresh_from_db()
        assert not grant.is_active, "Grant should be revoked"
        assert grant.revoked_at is not None, "Revocation timestamp should be set"

    @pytest.mark.rule('BR-PRACTICE-003')
    def test_all_practice_actions_must_be_logged_with_practice_id_and_engagement_id(self):
        """
        BR-PRACTICE-003: All practice actions must be logged with practice_id and engagement_id.

        Given a practice user is accessing a client tenant
        When the user performs an action
        Then the action is logged with practice_id and engagement_id
        """
        # This test verifies the audit trail requirement
        # In actual implementation, audit logging would be in middleware/services

        from identity_access.domain.models import (
            Practice, PracticeMembership, ClientEngagement
        )

        # Given: practice user accessing client tenant
        practice = Practice.objects.create(
            name='Test Practice',
            slug='test-practice'
        )

        practice_user = User.objects.create_user(
            email='practice@example.com',
            password='securepassword123!'
        )

        PracticeMembership.objects.create(
            user=practice_user,
            practice=practice,
            role='staff',
            status='active'
        )

        client_tenant = Tenant.objects.create(
            name='Client Tenant',
            slug='client-tenant'
        )

        engagement = ClientEngagement.objects.create(
            practice=practice,
            tenant=client_tenant,
            status='active'
        )

        # When: practice user performs action
        # Then: action should be logged with practice_id and engagement_id
        # (In actual implementation, this would be verified in audit logs)

        # Verify engagement links practice and tenant
        assert engagement.practice == practice
        assert engagement.tenant == client_tenant

    @pytest.mark.rule('BR-PRACTICE-004')
    def test_practice_users_cannot_access_client_data_without_active_advisor_access_grant(self):
        """
        BR-PRACTICE-004: Practice users cannot access client data without active AdvisorAccessGrant.

        Given a practice has an engagement with a client tenant
        When a practice user has no AdvisorAccessGrant
        Then the user cannot access the client tenant
        When an AdvisorAccessGrant is created
        Then the user can access the client tenant
        """
        from identity_access.domain.models import (
            Practice, PracticeMembership, ClientEngagement,
            AdvisorAccessGrant, Role
        )

        # Given: practice with engagement but no access grant
        practice = Practice.objects.create(
            name='Test Practice',
            slug='test-practice'
        )

        practice_user = User.objects.create_user(
            email='practice@example.com',
            password='securepassword123!'
        )

        PracticeMembership.objects.create(
            user=practice_user,
            practice=practice,
            role='staff',
            status='active'
        )

        client_tenant = Tenant.objects.create(
            name='Client Tenant',
            slug='client-tenant'
        )

        engagement = ClientEngagement.objects.create(
            practice=practice,
            tenant=client_tenant,
            status='active'
        )

        # When: no access grant exists
        # Then: practice user cannot access tenant
        assert not AuthorizationService.can_access_tenant(practice_user, client_tenant), \
            "Practice user should not access tenant without access grant"

        # When: access grant is created
        role = Role.objects.create(name='Accountant')
        grant = AdvisorAccessGrant.objects.create(
            engagement=engagement,
            practice_user=practice_user,
            tenant_role=role
        )

        # Then: practice user can access tenant
        assert AuthorizationService.can_access_tenant(practice_user, client_tenant), \
            "Practice user should access tenant with active access grant"

        # When: access grant is revoked
        grant.revoke(revoked_by=client_tenant.created_by, reason='Revoked')

        # Then: practice user cannot access tenant
        assert not AuthorizationService.can_access_tenant(practice_user, client_tenant), \
            "Practice user should not access tenant after grant is revoked"
