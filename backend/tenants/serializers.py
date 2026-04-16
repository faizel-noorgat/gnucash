from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from tenants.models import Tenant, TenantMembership

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'is_active', 'created_at', 'last_login_at')
        read_only_fields = ('id', 'created_at', 'last_login_at')


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ('id', 'name', 'slug', 'trial_ends_at', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class TenantMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = TenantMembership
        fields = ('id', 'tenant', 'user', 'user_email', 'role', 'joined_at')
        read_only_fields = ('id', 'joined_at')


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=12)
    tenant_name = serializers.CharField(write_only=True)
    tenant_slug = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'tenant_name', 'tenant_slug')
        read_only_fields = ('id',)

    def validate_password(self, value):
        if len(value) < 12:
            raise serializers.ValidationError('Password must be at least 12 characters.')
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError('Password must contain an uppercase letter.')
        if not any(c.islower() for c in value):
            raise serializers.ValidationError('Password must contain a lowercase letter.')
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError('Password must contain a digit.')
        return value

    def create(self, validated_data):
        tenant_name = validated_data.pop('tenant_name')
        tenant_slug = validated_data.pop('tenant_slug')
        password = validated_data.pop('password')

        from django.db import transaction
        from tenants.models import Tenant, TenantMembership

        with transaction.atomic():
            user = User.objects.create_user(email=validated_data['email'], password=password)
            tenant = Tenant.objects.create(name=tenant_name, slug=tenant_slug)
            TenantMembership.objects.create(tenant=tenant, user=user, role='OWNER')

        return user
