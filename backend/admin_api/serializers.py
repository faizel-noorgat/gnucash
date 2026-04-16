# backend/admin_api/serializers.py
from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from tenants.models import Tenant, TenantMembership

User = get_user_model()


class AdminTenantSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = (
            'id', 'name', 'slug', 'trial_ends_at', 'stripe_customer_id',
            'created_at', 'updated_at', 'member_count', 'owner_email',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_member_count(self, obj: Tenant) -> int:
        return obj.memberships.count()

    def get_owner_email(self, obj: Tenant) -> str | None:
        owner = obj.memberships.filter(role=TenantMembership.Role.OWNER).first()
        return owner.user.email if owner else None


class AdminTenantCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ('name', 'slug', 'trial_ends_at')

    def create(self, validated_data: dict) -> Tenant:
        return Tenant.objects.create(**validated_data)


class AdminTenantUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ('name', 'slug', 'trial_ends_at', 'stripe_customer_id')

    def update(self, instance: Tenant, validated_data: dict) -> Tenant:
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class AdminUserSerializer(serializers.ModelSerializer):
    tenant_count = serializers.SerializerMethodField()
    tenant_names = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'is_active', 'is_staff', 'is_superuser',
            'created_at', 'last_login_at', 'tenant_count', 'tenant_names',
        )
        read_only_fields = ('id', 'created_at', 'last_login_at')

    def get_tenant_count(self, obj: User) -> int:
        return obj.memberships.count()

    def get_tenant_names(self, obj: User) -> list[str]:
        return list(obj.memberships.values_list('tenant__name', flat=True))


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('is_active', 'is_staff', 'is_superuser')

    def update(self, instance: User, validated_data: dict) -> User:
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class AdminAuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()

    class Meta:
        model = 'audit.AuditLog'  # type: ignore[arg-type]
        fields = (
            'id', 'tenant', 'tenant_name', 'user', 'user_email', 'action',
            'model', 'object_id', 'old_values', 'new_values', 'ip_address',
            'user_agent', 'timestamp',
        )
        read_only_fields = (
            'id', 'tenant', 'tenant_name', 'user', 'user_email', 'action',
            'model', 'object_id', 'old_values', 'new_values', 'ip_address',
            'user_agent', 'timestamp',
        )

    def get_user_email(self, obj) -> str | None:  # type: ignore[no-untyped-def]
        return obj.user.email if obj.user else None

    def get_tenant_name(self, obj) -> str:  # type: ignore[no-untyped-def]
        return obj.tenant.name


class DashboardStatsSerializer(serializers.Serializer):
    total_tenants = serializers.IntegerField()
    total_users = serializers.IntegerField()
    total_audit_events = serializers.IntegerField()
    active_tenants_30d = serializers.IntegerField()
    recent_signups = serializers.IntegerField()
