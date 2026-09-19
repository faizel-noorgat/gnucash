"""
Integration Tests for API Endpoints
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from identity_access.domain.models import User, Tenant, Membership


@pytest.mark.integration
class TestAuthenticationAPI(TestCase):
    """Integration tests for authentication API endpoints."""

    databases = '__all__'

    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

    def test_register_user(self):
        """Test user registration endpoint."""
        response = self.client.post('/api/v1/auth/register/', {
            'email': 'new@example.com',
            'password': 'securepassword123!',
            'first_name': 'New',
            'last_name': 'User'
        })

        assert response.status_code == 201
        assert response.data['email'] == 'new@example.com'

    def test_login_success(self):
        """Test successful login."""
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'test@example.com',
            'password': 'securepassword123!'
        })

        assert response.status_code == 200
        assert 'access_token' in response.data
        assert 'refresh_token' in response.data

    def test_login_failure(self):
        """Test failed login."""
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })

        assert response.status_code == 401

    def test_get_current_user(self):
        """Test getting current user."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/auth/me/')

        assert response.status_code == 200
        assert response.data['email'] == 'test@example.com'

    def test_get_current_user_unauthenticated(self):
        """Test getting current user without authentication."""
        response = self.client.get('/api/v1/auth/me/')

        assert response.status_code in [401, 403]


@pytest.mark.integration
class TestTenantAPI(TestCase):
    """Integration tests for tenant API endpoints."""

    databases = '__all__'

    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )
        self.tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            created_by=self.user
        )
        Membership.objects.create(
            user=self.user,
            tenant=self.tenant,
            role='owner',
            status='active'
        )

    def test_list_tenants(self):
        """Test listing accessible tenants."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/tenants/')

        assert response.status_code == 200
        assert len(response.data['results']) > 0

    def test_get_tenant(self):
        """Test getting tenant details."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/v1/tenants/{self.tenant.slug}/')

        assert response.status_code == 200
        assert response.data['name'] == 'Test Tenant'

    def test_create_tenant(self):
        """Test creating a new tenant."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/tenants/', {
            'name': 'New Tenant',
            'slug': 'new-tenant'
        })

        assert response.status_code == 201
        assert response.data['name'] == 'New Tenant'


@pytest.mark.integration
class TestMembershipAPI(TestCase):
    """Integration tests for membership API endpoints."""

    databases = '__all__'

    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )
        self.tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            created_by=self.user
        )
        Membership.objects.create(
            user=self.user,
            tenant=self.tenant,
            role='owner',
            status='active'
        )

    def test_list_members(self):
        """Test listing tenant members."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/v1/tenants/{self.tenant.slug}/members/')

        assert response.status_code == 200
        assert len(response.data) > 0

    def test_invite_user(self):
        """Test inviting a user to tenant."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/v1/tenants/{self.tenant.slug}/members/invite/',
            {
                'email': 'invite@example.com',
                'role': 'accountant'
            }
        )

        assert response.status_code == 201


@pytest.mark.integration
class TestNotificationAPI(TestCase):
    """Integration tests for notification API endpoints."""

    databases = '__all__'

    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='securepassword123!'
        )

    def test_list_notifications(self):
        """Test listing notifications."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/notifications/')

        assert response.status_code == 200

    def test_get_unread_count(self):
        """Test getting unread notification count."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/notifications/unread-count/')

        assert response.status_code == 200
        assert 'count' in response.data
