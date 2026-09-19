"""
Base test case for business documents tests
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
# NOTE: UserFactory is deliberately NOT imported. It is defined locally further
# down this module and that class rebinds the module-global name, so importing
# it from factories.py would be dead code - and factories.py defines no
# UserFactory, which made this module raise ImportError on import.
from tests.business_documents.factories import TenantFactory, LegalEntityFactory

User = get_user_model()


class BaseTestCase(TestCase):
    """Base test case with common setup"""

    def setUp(self):
        """Set up test data"""
        self.tenant = TenantFactory()
        self.legal_entity = LegalEntityFactory(tenant=self.tenant)
        self.user = UserFactory()

        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Set tenant header
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.guid))


class UserFactory:
    """Factory for User model"""

    @staticmethod
    def create(**kwargs):
        """Create a user"""
        return User.objects.create_user(
            username=kwargs.get('username', 'testuser'),
            email=kwargs.get('email', 'test@example.com'),
            password=kwargs.get('password', 'testpass123'),
            **{k: v for k, v in kwargs.items() if k not in ['username', 'email', 'password']}
        )

    def __call__(self, **kwargs):
        return self.create(**kwargs)
