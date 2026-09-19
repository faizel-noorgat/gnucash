"""
API Serializers Package
"""

from rest_framework import serializers
from ..domain.models import (
    User, Tenant, LegalEntity, Membership, Role, Permission,
    ApiToken, Practice, PracticeMembership, ClientEngagement,
    AdvisorAccessGrant, Notification, NotificationPreference
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = [
            'guid', 'email', 'first_name', 'last_name', 'phone_number',
            'timezone', 'language', 'mfa_enabled', 'is_active', 'is_verified',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['guid', 'created_at', 'updated_at']


class UserRegistrationSerializer(serializers.Serializer):
    """Serializer for user registration."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=12)
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)

    def validate_email(self, value):
        """Validate email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value


class TenantSerializer(serializers.ModelSerializer):
    """Serializer for Tenant model."""

    class Meta:
        model = Tenant
        fields = [
            'guid', 'name', 'slug', 'description', 'organization_name',
            'business_registration_number', 'tax_identification_number',
            'contact_email', 'contact_phone', 'address_line1', 'address_line2',
            'city', 'state', 'postal_code', 'country', 'is_active', 'is_verified',
            'default_currency', 'fiscal_year_start_month',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['guid', 'created_at', 'updated_at']


class LegalEntitySerializer(serializers.ModelSerializer):
    """Serializer for LegalEntity model."""

    class Meta:
        model = LegalEntity
        fields = [
            'guid', 'tenant', 'name', 'legal_name', 'registration_number',
            'tax_identification_number', 'entity_type', 'base_currency',
            'fiscal_year_start_month', 'accounting_standard',
            'contact_email', 'contact_phone', 'address_line1', 'address_line2',
            'city', 'state', 'postal_code', 'country', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['guid', 'created_at', 'updated_at']


class MembershipSerializer(serializers.ModelSerializer):
    """Serializer for Membership model."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = [
            'guid', 'user', 'tenant', 'role', 'status', 'invited_by',
            'invited_at', 'accepted_at', 'scoped_entity',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['guid', 'created_at', 'updated_at', 'user']


class MembershipInviteSerializer(serializers.Serializer):
    """Serializer for inviting user to tenant."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=Membership.ROLE_CHOICES)
    scoped_entity = serializers.UUIDField(required=False, allow_null=True)


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model."""

    class Meta:
        model = Role
        fields = ['guid', 'name', 'description', 'tenant', 'is_system_role', 'is_active']
        read_only_fields = ['guid']


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Permission model."""

    class Meta:
        model = Permission
        fields = ['guid', 'name', 'codename', 'description', 'category', 'is_active']
        read_only_fields = ['guid']


class ApiTokenSerializer(serializers.ModelSerializer):
    """Serializer for ApiToken model."""

    class Meta:
        model = ApiToken
        fields = [
            'guid', 'name', 'token_prefix', 'permissions', 'expires_at',
            'is_active', 'last_used_at', 'usage_count', 'created_at'
        ]
        read_only_fields = ['guid', 'token_prefix', 'last_used_at', 'usage_count', 'created_at']


class ApiTokenCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ApiToken."""

    class Meta:
        model = ApiToken
        fields = ['name', 'permissions', 'expires_at', 'tenant']

    def create(self, validated_data):
        """Create API token and return token value."""
        user = self.context['request'].user
        token = ApiToken.objects.create(
            user=user,
            created_by=user,
            **validated_data
        )
        # Return token value only on creation
        return {'token': token.token, 'api_token': token}


class PracticeSerializer(serializers.ModelSerializer):
    """Serializer for Practice model."""

    class Meta:
        model = Practice
        fields = [
            'guid', 'name', 'slug', 'description', 'contact_email',
            'contact_phone', 'website', 'address_line1', 'address_line2',
            'city', 'state', 'postal_code', 'country',
            'business_registration_number', 'tax_identification_number',
            'is_active', 'is_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['guid', 'created_at', 'updated_at']


class PracticeMembershipSerializer(serializers.ModelSerializer):
    """Serializer for PracticeMembership model."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = PracticeMembership
        fields = [
            'guid', 'user', 'practice', 'role', 'status',
            'invited_at', 'accepted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['guid', 'created_at', 'updated_at', 'user']


class ClientEngagementSerializer(serializers.ModelSerializer):
    """Serializer for ClientEngagement model."""

    practice = PracticeSerializer(read_only=True)
    tenant = TenantSerializer(read_only=True)

    class Meta:
        model = ClientEngagement
        fields = [
            'guid', 'practice', 'tenant', 'name', 'description', 'status',
            'engagement_type', 'started_at', 'ended_at',
            'contract_start_date', 'contract_end_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['guid', 'created_at', 'updated_at']


class AdvisorAccessGrantSerializer(serializers.ModelSerializer):
    """Serializer for AdvisorAccessGrant model."""

    practice_user = UserSerializer(read_only=True)
    tenant_role = RoleSerializer(read_only=True)

    class Meta:
        model = AdvisorAccessGrant
        fields = [
            'guid', 'engagement', 'practice_user', 'tenant_role',
            'scoped_entity', 'granted_at', 'expires_at', 'revoked_at',
            'reason', 'created_at', 'updated_at'
        ]
        read_only_fields = ['guid', 'granted_at', 'revoked_at', 'created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""

    class Meta:
        model = Notification
        fields = [
            'guid', 'notification_type', 'title', 'message', 'is_read',
            'read_at', 'action_url', 'created_at'
        ]
        read_only_fields = ['guid', 'created_at', 'read_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model."""

    class Meta:
        model = NotificationPreference
        fields = [
            'guid', 'tenant', 'preferences', 'quiet_hours_enabled',
            'quiet_hours_start', 'quiet_hours_end', 'quiet_hours_timezone'
        ]
        read_only_fields = ['guid']
