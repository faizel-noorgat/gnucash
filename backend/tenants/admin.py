from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

from tenants.models import Tenant, TenantMembership, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'email', 'is_active', 'is_staff', 'date_joined', 'last_login')
    list_filter = ('is_active', 'is_staff', 'date_joined')
    search_fields = ('email',)
    readonly_fields = ('id', 'date_joined', 'last_login')
    ordering = ('-date_joined',)
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2')}),
    )


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'trial_ends_at', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'slug')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'user', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('tenant__name', 'user__email')
    readonly_fields = ('id', 'joined_at')
    ordering = ('-joined_at',)
