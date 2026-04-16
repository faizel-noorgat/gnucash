from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestAuthRegistration:
    def test_register_creates_user_and_tenant(self, api_client):
        response = api_client.post('/api/v1/auth/register/', {
            'email': 'newuser@example.com',
            'password': 'StrongP@ssw0rd123',
            'tenant_name': 'My Household',
            'tenant_slug': 'my-household',
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['email'] == 'newuser@example.com'

    def test_register_weak_password_rejected(self, api_client):
        response = api_client.post('/api/v1/auth/register/', {
            'email': 'newuser@example.com',
            'password': 'weak',
            'tenant_name': 'My Household',
            'tenant_slug': 'my-household',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email_rejected(self, api_client):
        api_client.post('/api/v1/auth/register/', {
            'email': 'dup@example.com',
            'password': 'StrongP@ssw0rd123',
            'tenant_name': 'First',
            'tenant_slug': 'first',
        })

        response = api_client.post('/api/v1/auth/register/', {
            'email': 'dup@example.com',
            'password': 'StrongP@ssw0rd123',
            'tenant_name': 'Second',
            'tenant_slug': 'second',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_returns_tokens(self, api_client):
        api_client.post('/api/v1/auth/register/', {
            'email': 'loginuser@example.com',
            'password': 'StrongP@ssw0rd123',
            'tenant_name': 'Login Test',
            'tenant_slug': 'login-test',
        })

        response = api_client.post('/api/v1/auth/login/', {
            'email': 'loginuser@example.com',
            'password': 'StrongP@ssw0rd123',
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
