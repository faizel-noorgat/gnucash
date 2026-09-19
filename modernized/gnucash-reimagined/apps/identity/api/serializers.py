"""
Identity API Serializers

Stub serializer module for the Identity & Access API.
Implement DRF serializers here as endpoints are built out.
"""

# from rest_framework import serializers
# from apps.identity.models import User, Tenant
#
#
# class UserSerializer(serializers.ModelSerializer):
#     """Serializer for the platform User model."""
#
#     class Meta:
#         model = User
#         fields = [
#             'guid', 'email', 'username', 'first_name', 'last_name',
#             'phone_number', 'timezone', 'language',
#             'mfa_enabled', 'is_active', 'is_verified',
#             'created_at', 'updated_at',
#         ]
#         read_only_fields = ['guid', 'created_at', 'updated_at']
#
#
# class TenantSerializer(serializers.ModelSerializer):
#     """Serializer for the Tenant (SME customer organization) model."""
#
#     class Meta:
#         model = Tenant
#         fields = [
#             'guid', 'name', 'slug', 'description',
#             'organization_name', 'contact_email',
#             'is_active', 'is_verified',
#             'default_currency', 'fiscal_year_start_month',
#             'created_at', 'updated_at',
#         ]
#         read_only_fields = ['guid', 'created_at', 'updated_at']
