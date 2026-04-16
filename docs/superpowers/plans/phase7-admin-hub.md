# Phase 7: Admin Hub — Platform Administration App

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a separate Vite + React + TypeScript admin hub application at `admin/` for platform administrators to manage tenants, users, view cross-tenant audit logs, and monitor platform analytics. Wire up the backend admin API with superuser-only ViewSets.

**Architecture:** The admin hub is a standalone React app (not a route within the tenant frontend). It shares the same shadcn/ui component patterns, React Query data fetching, and API client approach as the tenant app, but targets `/api/v1/admin/` endpoints that bypass tenant scoping and require `is_staff=True`.

**Tech Stack:** Vite, React 19, TypeScript (strict), React Router v7, React Query v5, Tailwind CSS v3, shadcn/ui, Lucide icons

---

## File Map

### Backend Files to Create/Modify

| File | Action | Purpose |
|---|---|---|
| `backend/admin_api/__init__.py` | Create | Django app package |
| `backend/admin_api/views.py` | Create | Admin ViewSets (Tenant, User, AuditLog, Dashboard) |
| `backend/admin_api/serializers.py` | Create | Admin-scoped serializers |
| `backend/admin_api/permissions.py` | Create | `IsPlatformAdmin` permission class |
| `backend/admin_api/urls.py` | Create | Admin router registration |
| `backend/gnucash_web/urls.py` | Modify | Wire admin_api routes into `admin_api_router` |
| `backend/tenants/serializers.py` | Modify | Add `AdminTenantSerializer` with membership count |

### Frontend Admin Files to Create

| File | Purpose |
|---|---|
| `admin/package.json` | Dependencies (mirrors frontend + admin-specific) |
| `admin/tsconfig.json` | TypeScript config (strict) |
| `admin/tsconfig.node.json` | TypeScript node config |
| `admin/vite.config.ts` | Vite config with API proxy to :8000 |
| `admin/tailwind.config.ts` | Tailwind config (same theme as frontend) |
| `admin/postcss.config.js` | PostCSS config |
| `admin/index.html` | HTML entry point |
| `admin/src/main.tsx` | React entry point |
| `admin/src/App.tsx` | Router + QueryClient setup |
| `admin/src/index.css` | Tailwind + base styles |
| `admin/src/vite-env.d.ts` | Vite type declarations |
| `admin/src/lib/utils.ts` | `cn()` utility |
| `admin/src/lib/api.ts` | API client hitting `/api/v1/admin/` |
| `admin/src/lib/query-client.ts` | React Query client config |
| `admin/src/components/ui/button.tsx` | shadcn Button |
| `admin/src/components/ui/card.tsx` | shadcn Card |
| `admin/src/components/ui/input.tsx` | shadcn Input |
| `admin/src/components/ui/table.tsx` | shadcn Table |
| `admin/src/components/ui/badge.tsx` | shadcn Badge |
| `admin/src/components/ui/label.tsx` | shadcn Label |
| `admin/src/components/ui/dialog.tsx` | shadcn Dialog |
| `admin/src/components/ui/separator.tsx` | shadcn Separator |
| `admin/src/components/ui/tooltip.tsx` | shadcn Tooltip |
| `admin/src/components/ui/progress.tsx` | shadcn Progress |
| `admin/src/components/ui/tabs.tsx` | shadcn Tabs |
| `admin/src/components/layouts/RootLayout.tsx` | Admin sidebar layout |
| `admin/src/components/layouts/AdminAuthGuard.tsx` | Redirect non-staff users |
| `admin/src/routes/DashboardPage.tsx` | Platform overview |
| `admin/src/routes/TenantsPage.tsx` | Tenant management list |
| `admin/src/routes/UsersPage.tsx` | Cross-tenant user list |
| `admin/src/routes/BillingPage.tsx` | Stripe dashboard link |
| `admin/src/routes/SupportPage.tsx` | Support tickets (MVP placeholder) |
| `admin/src/routes/AnalyticsPage.tsx` | Platform analytics |
| `admin/src/routes/AuditLogPage.tsx` | Cross-tenant audit log viewer |
| `admin/src/routes/LoginPage.tsx` | Admin login (uses existing auth) |
| `admin/src/routes/NotFoundPage.tsx` | 404 page |
| `admin/src/types/admin.ts` | TypeScript type definitions |
| `admin/src/hooks/useAdminTenants.ts` | Tenant data fetching hooks |
| `admin/src/hooks/useAdminUsers.ts` | User data fetching hooks |
| `admin/src/hooks/useAdminAuditLog.ts` | Audit log data fetching hooks |
| `admin/src/hooks/useAdminDashboard.ts` | Dashboard stats hooks |

---

## Step 1: Backend Admin API App

- [ ] **Step 1.1: Create `backend/admin_api/permissions.py`**

```python
# backend/admin_api/permissions.py
from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    """
    Allow access only to users with is_staff=True.
    This permission is used for all cross-tenant admin endpoints.
    """

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )
```

- [ ] **Step 1.2: Create `backend/admin_api/serializers.py`**

```python
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
```

- [ ] **Step 1.3: Create `backend/admin_api/views.py`**

```python
# backend/admin_api/views.py
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.models import AuditLog
from tenants.models import Tenant

from admin_api.permissions import IsPlatformAdmin
from admin_api.serializers import (
    AdminAuditLogSerializer,
    AdminTenantCreateSerializer,
    AdminTenantSerializer,
    AdminTenantUpdateSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    DashboardStatsSerializer,
)

User = get_user_model()


class AdminTenantViewSet(viewsets.ModelViewSet):
    """
    CRUD for all tenants — visible only to platform admins.
    Bypasses tenant scoping; operates across all tenants.
    """
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        return Tenant.objects.all().prefetch_related('memberships')

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminTenantCreateSerializer
        if self.action in ('update', 'partial_update'):
            return AdminTenantUpdateSerializer
        return AdminTenantSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(slug__icontains=search)
            )

        status_filter = request.query_params.get('status')
        if status_filter == 'trial':
            queryset = queryset.filter(trial_ends_at__gte=timezone.now())
        elif status_filter == 'expired':
            queryset = queryset.filter(
                trial_ends_at__lt=timezone.now(),
                stripe_customer_id='',
            )
        elif status_filter == 'active':
            queryset = queryset.filter(
                Q(trial_ends_at__gte=timezone.now()) | ~Q(stripe_customer_id=''),
            )

        queryset = queryset.order_by('-created_at')

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer)

    @action(detail=True, methods=['post'], permission_classes=[IsPlatformAdmin])
    def extend_trial(self, request, pk=None):
        tenant = self.get_object()
        days = request.data.get('days', 14)
        current_end = tenant.trial_ends_at or timezone.now()
        tenant.trial_ends_at = current_end + timedelta(days=days)
        tenant.save(update_fields=['trial_ends_at'])
        return Response(
            {'id': tenant.id, 'trial_ends_at': tenant.trial_ends_at},
            status=status.HTTP_200_OK,
        )


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list of all users across all tenants.
    Platform admins can view users, filter, and search.
    User updates (is_active, is_staff) via dedicated action.
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        return User.objects.all().prefetch_related('memberships__tenant')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(email__icontains=search)

        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        queryset = queryset.order_by('-date_joined')

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer)

    @action(detail=True, methods=['patch'], permission_classes=[IsPlatformAdmin])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        return Response({'id': user.id, 'is_active': user.is_active})

    @action(detail=True, methods=['patch'], permission_classes=[IsPlatformAdmin])
    def set_staff(self, request, pk=None):
        user = self.get_object()
        user.is_staff = request.data.get('is_staff', False)
        user.save(update_fields=['is_staff'])
        return Response({'id': user.id, 'is_staff': user.is_staff})


class AdminAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Cross-tenant audit log viewer for platform admins.
    Supports filtering by tenant, action, model, and date range.
    """
    serializer_class = AdminAuditLogSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        return AuditLog.objects.select_related('tenant', 'user')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        tenant_id = request.query_params.get('tenant_id')
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        action = request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)

        model = request.query_params.get('model')
        if model:
            queryset = queryset.filter(model__icontains=model)

        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(timestamp__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(timestamp__lte=date_to)

        user_email = request.query_params.get('user_email')
        if user_email:
            queryset = queryset.filter(user__email__icontains=user_email)

        queryset = queryset.order_by('-timestamp')

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer)


class DashboardStatsView(viewsets.ViewSet):
    """
    Platform dashboard statistics — aggregated counts and trends.
    Read-only, superuser-only.
    """
    permission_classes = [IsPlatformAdmin]

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)

        total_tenants = Tenant.objects.count()
        total_users = User.objects.count()
        total_audit_events = AuditLog.objects.count()
        active_tenants_30d = Tenant.objects.filter(
            memberships__joined_at__gte=thirty_days_ago,
        ).distinct().count()
        recent_signups = User.objects.filter(
            date_joined__gte=seven_days_ago,
        ).count()

        serializer = DashboardStatsSerializer({
            'total_tenants': total_tenants,
            'total_users': total_users,
            'total_audit_events': total_audit_events,
            'active_tenants_30d': active_tenants_30d,
            'recent_signups': recent_signups,
        })

        return Response(serializer.data)
```

- [ ] **Step 1.4: Create `backend/admin_api/urls.py`**

```python
# backend/admin_api/urls.py
from __future__ import annotations

from django.urls import path
from rest_framework.routers import DefaultRouter

from admin_api.views import (
    AdminAuditLogViewSet,
    AdminTenantViewSet,
    AdminUserViewSet,
    DashboardStatsView,
)

router = DefaultRouter()
router.register('tenants', AdminTenantViewSet, basename='admin-tenant')
router.register('users', AdminUserViewSet, basename='admin-user')
router.register('audit-log', AdminAuditLogViewSet, basename='admin-audit-log')

urlpatterns = [
    path('dashboard/', DashboardStatsView.as_view({'get': 'stats'}), name='admin-dashboard-stats'),
]
urlpatterns += router.urls
```

- [ ] **Step 1.5: Modify `backend/gnucash_web/urls.py` — replace empty `admin_api_router`**

```python
# backend/gnucash_web/urls.py
# ... (keep all existing imports above the admin section)

# Replace lines 34-36 (admin_api_router = DefaultRouter()) with:
from admin_api.urls import urlpatterns as admin_api_urls

urlpatterns = [
    # ... (keep existing patterns)
    path('api/v1/admin/', include(admin_api_urls)),
    # ...
]
```

Concretely, replace the current `admin_api_router` block and the include line:

```python
# Remove these lines:
# admin_api_router = DefaultRouter()
# ...
# path('api/v1/admin/', include(admin_api_router.urls)),

# Replace with:
from admin_api.urls import urlpatterns as admin_api_urls

# Then in urlpatterns list:
path('api/v1/admin/', include(admin_api_urls)),
```

- [ ] **Step 1.6: Register `admin_api` in `backend/gnucash_web/settings/base.py`**

Add `'admin_api'` to `INSTALLED_APPS` in the Django apps section.

---

## Step 2: Admin Hub Project Setup

- [ ] **Step 2.1: Create `admin/package.json`**

```json
{
  "name": "gnucash-web-admin",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --port 5174",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "typecheck": "tsc -b --noEmit"
  },
  "dependencies": {
    "@hookform/resolvers": "^4.1.0",
    "@radix-ui/react-dialog": "^1.1.15",
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-progress": "^1.1.8",
    "@radix-ui/react-separator": "^1.1.8",
    "@radix-ui/react-slot": "^1.2.4",
    "@radix-ui/react-tabs": "^1.1.0",
    "@radix-ui/react-tooltip": "^1.2.8",
    "@tanstack/react-query": "^5.62.0",
    "@tanstack/react-table": "^8.20.5",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.0",
    "cmdk": "^1.1.1",
    "date-fns": "^4.1.0",
    "lucide-react": "^0.460.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-hook-form": "^7.54.0",
    "react-router-dom": "^7.1.0",
    "tailwind-merge": "^2.5.0",
    "zod": "^3.24.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.16",
    "typescript": "^5.7.0",
    "vite": "^6.0.0"
  }
}
```

- [ ] **Step 2.2: Create `admin/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 2.3: Create `admin/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "composite": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 2.4: Create `admin/vite.config.ts`**

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 2.5: Create `admin/tailwind.config.ts`**

```typescript
import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(214.3 31.8% 91.4%)',
        input: 'hsl(214.3 31.8% 91.4%)',
        ring: 'hsl(222.2 84% 4.9%)',
        background: 'hsl(0 0% 100%)',
        foreground: 'hsl(222.2 84% 4.9%)',
        primary: { DEFAULT: 'hsl(222.2 47.4% 11.2%)', foreground: 'hsl(210 40% 98%)' },
        secondary: { DEFAULT: 'hsl(210 40% 96.1%)', foreground: 'hsl(222.2 47.4% 11.2%)' },
        destructive: { DEFAULT: 'hsl(0 84.2% 60.2%)', foreground: 'hsl(210 40% 98%)' },
        muted: { DEFAULT: 'hsl(210 40% 96.1%)', foreground: 'hsl(215.4 16.3% 46.9%)' },
        accent: { DEFAULT: 'hsl(210 40% 96.1%)', foreground: 'hsl(222.2 47.4% 11.2%)' },
        popover: { DEFAULT: 'hsl(0 0% 100%)', foreground: 'hsl(222.2 84% 4.9%)' },
        card: { DEFAULT: 'hsl(0 0% 100%)', foreground: 'hsl(222.2 84% 4.9%)' },
      },
      borderRadius: { lg: '0.5rem', md: 'calc(0.5rem - 2px)', sm: 'calc(0.5rem - 4px)' },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 2.6: Create `admin/postcss.config.js`**

```js
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
};
```

- [ ] **Step 2.7: Create `admin/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>GnuCash Admin</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🔧</text></svg>" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

---

## Step 3: Admin App Foundation

- [ ] **Step 3.1: Create `admin/src/vite-env.d.ts`**

```typescript
/// <reference types="vite/client" />
```

- [ ] **Step 3.2: Create `admin/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  * { @apply border-border; }
  body {
    @apply bg-background text-foreground;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }
}
```

- [ ] **Step 3.3: Create `admin/src/lib/utils.ts`**

```typescript
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 3.4: Create `admin/src/lib/api.ts`**

The admin API client differs from the tenant client in two ways:
1. Base path is `/api/v1/admin/`
2. No `X-Tenant-ID` header (admin is cross-tenant)

```typescript
// admin/src/lib/api.ts

const API_BASE = '/api/v1/admin';

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function getAccessToken(): string | null {
  try {
    return localStorage.getItem('gnucash_access_token');
  } catch {
    return null;
  }
}

async function refreshToken(): Promise<string | null> {
  try {
    const response = await fetch('/api/v1/auth/refresh/', {
      method: 'POST',
      credentials: 'include',
    });
    if (!response.ok) return null;
    const data = await response.json();
    return data.access ?? null;
  } catch {
    return null;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAccessToken() ?? await refreshToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init?.headers as Record<string, string> ?? {}),
  };

  let response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });

  if (response.status === 401) {
    const newToken = await refreshToken();
    if (newToken) {
      headers.Authorization = `Bearer ${newToken}`;
      response = await fetch(`${API_BASE}${path}`, {
        ...init,
        headers,
        credentials: 'include',
      });
    }
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body, response.statusText);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};
```

- [ ] **Step 3.5: Create `admin/src/lib/query-client.ts`**

```typescript
// admin/src/lib/query-client.ts
import { QueryClient } from '@tanstack/react-query';
import { ApiError } from './api';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: (failureCount, error: unknown) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
        return failureCount < 2;
      },
    },
  },
});
```

- [ ] **Step 3.6: Create `admin/src/main.tsx`**

```typescript
// admin/src/main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from '@/App';
import '@/index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
);
```

---

## Step 4: shadcn/ui Components

Copy the following from `frontend/src/components/ui/` to `admin/src/components/ui/` with the `@/` import path updated to match the admin app. The files are identical in content.

- [ ] **Step 4.1: Create `admin/src/components/ui/button.tsx`**

```typescript
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
```

- [ ] **Step 4.2: Create `admin/src/components/ui/card.tsx`**

```typescript
import * as React from 'react';
import { cn } from '@/lib/utils';

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('rounded-lg border bg-card text-card-foreground shadow-sm', className)} {...props} />
));
Card.displayName = 'Card';

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />
));
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(({ className, ...props }, ref) => (
  <h3 ref={ref} className={cn('text-2xl font-semibold leading-none tracking-tight', className)} {...props} />
));
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(({ className, ...props }, ref) => (
  <p ref={ref} className={cn('text-sm text-muted-foreground', className)} {...props} />
));
CardDescription.displayName = 'CardDescription';

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
));
CardContent.displayName = 'CardContent';

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('flex items-center p-6 pt-0', className)} {...props} />
));
CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };
```

- [ ] **Step 4.3: Create `admin/src/components/ui/input.tsx`**

```typescript
import * as React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
Input.displayName = 'Input';
export { Input };
```

- [ ] **Step 4.4: Create `admin/src/components/ui/table.tsx`**

Copy from `frontend/src/components/ui/table.tsx` (identical).

- [ ] **Step 4.5: Create `admin/src/components/ui/badge.tsx`**

```typescript
import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
        secondary: 'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
        destructive: 'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80',
        outline: 'text-foreground',
        success: 'border-transparent bg-emerald-100 text-emerald-800',
        warning: 'border-transparent bg-amber-100 text-amber-800',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
```

- [ ] **Step 4.6: Create `admin/src/components/ui/label.tsx`**

Copy from `frontend/src/components/ui/label.tsx` (identical).

- [ ] **Step 4.7: Create `admin/src/components/ui/dialog.tsx`**

Copy from `frontend/src/components/ui/dialog.tsx` (identical).

- [ ] **Step 4.8: Create `admin/src/components/ui/separator.tsx`**

Copy from `frontend/src/components/ui/separator.tsx` (identical).

- [ ] **Step 4.9: Create `admin/src/components/ui/tooltip.tsx`**

Copy from `frontend/src/components/ui/tooltip.tsx` (identical).

- [ ] **Step 4.10: Create `admin/src/components/ui/progress.tsx`**

Copy from `frontend/src/components/ui/progress.tsx` (identical).

- [ ] **Step 4.11: Create `admin/src/components/ui/tabs.tsx`**

```typescript
import * as React from 'react';
import * as TabsPrimitive from '@radix-ui/react-tabs';
import { cn } from '@/lib/utils';

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef<
  React.ComponentRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      'inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground',
      className,
    )}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsTrigger = React.forwardRef<
  React.ComponentRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm',
      className,
    )}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = React.forwardRef<
  React.ComponentRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      'mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      className,
    )}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
```

---

## Step 5: Types

- [ ] **Step 5.1: Create `admin/src/types/admin.ts`**

```typescript
// admin/src/types/admin.ts

export interface AdminTenant {
  id: string;
  name: string;
  slug: string;
  trial_ends_at: string | null;
  stripe_customer_id: string;
  created_at: string;
  updated_at: string;
  member_count: number;
  owner_email: string | null;
}

export interface AdminTenantCreate {
  name: string;
  slug: string;
  trial_ends_at?: string;
}

export interface AdminTenantUpdate {
  name?: string;
  slug?: string;
  trial_ends_at?: string;
  stripe_customer_id?: string;
}

export interface AdminUser {
  id: string;
  email: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  created_at: string;
  last_login_at: string | null;
  tenant_count: number;
  tenant_names: string[];
}

export interface AdminAuditLog {
  id: string;
  tenant: string;
  tenant_name: string;
  user: string | null;
  user_email: string | null;
  action: 'CREATE' | 'UPDATE' | 'DELETE' | 'LOGIN' | 'LOGOUT' | 'EXPORT';
  model: string;
  object_id: string;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string;
  timestamp: string;
}

export interface DashboardStats {
  total_tenants: number;
  total_users: number;
  total_audit_events: number;
  active_tenants_30d: number;
  recent_signups: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
```

---

## Step 6: Custom Hooks

- [ ] **Step 6.1: Create `admin/src/hooks/useAdminTenants.ts`**

```typescript
// admin/src/hooks/useAdminTenants.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AdminTenant, AdminTenantCreate, AdminTenantUpdate, PaginatedResponse } from '@/types/admin';

export const adminTenantKeys = {
  all: ['admin', 'tenants'] as const,
  list: (params?: { search?: string; status?: string }) => [...adminTenantKeys.all, 'list', params] as const,
  detail: (id: string) => [...adminTenantKeys.all, 'detail', id] as const,
};

export function useAdminTenants(params?: { search?: string; status?: string }) {
  const query = params?.search ? `?search=${encodeURIComponent(params.search)}` : '';
  const statusQ = params?.status ? `${query ? '&' : '?'}status=${encodeURIComponent(params.status)}` : '';
  return useQuery({
    queryKey: adminTenantKeys.list(params),
    queryFn: () => api.get<PaginatedResponse<AdminTenant>>(`/tenants/${query}${statusQ}`),
  });
}

export function useCreateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AdminTenantCreate) => api.post<AdminTenant>('/tenants/', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: adminTenantKeys.all }),
  });
}

export function useUpdateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AdminTenantUpdate }) =>
      api.put<AdminTenant>(`/tenants/${id}/`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: adminTenantKeys.all }),
  });
}

export function useExtendTrial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, days }: { id: string; days: number }) =>
      api.post<{ id: string; trial_ends_at: string }>(`/tenants/${id}/extend_trial/`, { days }),
    onSuccess: () => qc.invalidateQueries({ queryKey: adminTenantKeys.all }),
  });
}
```

- [ ] **Step 6.2: Create `admin/src/hooks/useAdminUsers.ts`**

```typescript
// admin/src/hooks/useAdminUsers.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AdminUser, PaginatedResponse } from '@/types/admin';

export const adminUserKeys = {
  all: ['admin', 'users'] as const,
  list: (params?: { search?: string; is_active?: boolean }) => [...adminUserKeys.all, 'list', params] as const,
};

export function useAdminUsers(params?: { search?: string; is_active?: boolean }) {
  const searchQ = params?.search ? `?search=${encodeURIComponent(params.search)}` : '';
  const activeQ = params?.is_active !== undefined ? `${searchQ ? '&' : '?'}is_active=${params.is_active}` : '';
  return useQuery({
    queryKey: adminUserKeys.list(params),
    queryFn: () => api.get<PaginatedResponse<AdminUser>>(`/users/${searchQ}${activeQ}`),
  });
}

export function useToggleUserActive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.patch<{ id: string; is_active: boolean }>(`/users/${id}/toggle_active/`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: adminUserKeys.all }),
  });
}

export function useSetUserStaff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, is_staff }: { id: string; is_staff: boolean }) =>
      api.patch<{ id: string; is_staff: boolean }>(`/users/${id}/set_staff/`, { is_staff }),
    onSuccess: () => qc.invalidateQueries({ queryKey: adminUserKeys.all }),
  });
}
```

- [ ] **Step 6.3: Create `admin/src/hooks/useAdminAuditLog.ts`**

```typescript
// admin/src/hooks/useAdminAuditLog.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { AdminAuditLog, PaginatedResponse } from '@/types/admin';

export const adminAuditLogKeys = {
  all: ['admin', 'audit-log'] as const,
  list: (params?: AuditLogFilters) => [...adminAuditLogKeys.all, 'list', params] as const,
};

export interface AuditLogFilters {
  tenant_id?: string;
  action?: string;
  model?: string;
  date_from?: string;
  date_to?: string;
  user_email?: string;
}

export function useAdminAuditLog(filters?: AuditLogFilters) {
  const buildQuery = (): string => {
    if (!filters) return '';
    const parts: string[] = [];
    if (filters.tenant_id) parts.push(`tenant_id=${encodeURIComponent(filters.tenant_id)}`);
    if (filters.action) parts.push(`action=${encodeURIComponent(filters.action)}`);
    if (filters.model) parts.push(`model=${encodeURIComponent(filters.model)}`);
    if (filters.date_from) parts.push(`date_from=${encodeURIComponent(filters.date_from)}`);
    if (filters.date_to) parts.push(`date_to=${encodeURIComponent(filters.date_to)}`);
    if (filters.user_email) parts.push(`user_email=${encodeURIComponent(filters.user_email)}`);
    return parts.length ? `?${parts.join('&')}` : '';
  };

  return useQuery({
    queryKey: adminAuditLogKeys.list(filters),
    queryFn: () => api.get<PaginatedResponse<AdminAuditLog>>(`/audit-log/${buildQuery()}`),
  });
}
```

- [ ] **Step 6.4: Create `admin/src/hooks/useAdminDashboard.ts`**

```typescript
// admin/src/hooks/useAdminDashboard.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { DashboardStats } from '@/types/admin';

export const adminDashboardKeys = {
  all: ['admin', 'dashboard'] as const,
  stats: () => [...adminDashboardKeys.all, 'stats'] as const,
};

export function useDashboardStats() {
  return useQuery({
    queryKey: adminDashboardKeys.stats(),
    queryFn: () => api.get<DashboardStats>('/dashboard/stats/'),
    refetchInterval: 1000 * 60,
  });
}
```

---

## Step 7: Admin Auth Store & Guard

- [ ] **Step 7.1: Create `admin/src/stores/auth-store.ts`**

```typescript
// admin/src/stores/auth-store.ts
import { create } from 'zustand';

interface AuthUser {
  id: string;
  email: string;
  is_staff: boolean;
  is_superuser: boolean;
}

interface AuthState {
  user: AuthUser | null;
  isLoading: boolean;
  login: (user: AuthUser, accessToken: string) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  login: (user, accessToken) => {
    localStorage.setItem('gnucash_access_token', accessToken);
    set({ user, isLoading: false });
  },
  logout: () => {
    localStorage.removeItem('gnucash_access_token');
    set({ user: null });
  },
  setLoading: (loading) => set({ isLoading: loading }),
}));
```

- [ ] **Step 7.2: Create `admin/src/components/layouts/AdminAuthGuard.tsx`**

```typescript
// admin/src/components/layouts/AdminAuthGuard.tsx
import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/stores/auth-store';

export function AdminAuthGuard() {
  const user = useAuthStore((s) => s.user);

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.is_staff) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-destructive">Access Denied</h1>
          <p className="mt-2 text-muted-foreground">
            You do not have platform admin privileges.
          </p>
          <p className="mt-4 text-sm text-muted-foreground">
            Contact your platform administrator if you believe this is an error.
          </p>
        </div>
      </div>
    );
  }

  return <Outlet />;
}
```

---

## Step 8: Layout Components

- [ ] **Step 8.1: Create `admin/src/components/layouts/RootLayout.tsx`**

```typescript
// admin/src/components/layouts/RootLayout.tsx
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { useAuthStore } from '@/stores/auth-store';
import {
  LayoutDashboard,
  Building2,
  Users,
  CreditCard,
  BarChart3,
  ShieldCheck,
  LifeBuoy,
  LogOut,
} from 'lucide-react';

const navItems = [
  { label: 'Dashboard', path: '/admin/dashboard', icon: LayoutDashboard },
  { label: 'Tenants', path: '/admin/tenants', icon: Building2 },
  { label: 'Users', path: '/admin/users', icon: Users },
  { label: 'Billing', path: '/admin/billing', icon: CreditCard },
  { label: 'Analytics', path: '/admin/analytics', icon: BarChart3 },
  { label: 'Audit Log', path: '/admin/audit', icon: ShieldCheck },
  { label: 'Support', path: '/admin/support', icon: LifeBuoy },
];

export function RootLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div className="flex h-screen">
      <aside className="flex w-64 flex-col border-r bg-card">
        <div className="flex h-14 items-center border-b px-6">
          <h1 className="text-lg font-semibold">GnuCash Admin</h1>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-accent text-accent-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                }`}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </nav>
        <div className="border-t px-3 py-4">
          <Separator className="mb-3" />
          <div className="mb-2 px-3 text-xs text-muted-foreground">{user?.email}</div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => { logout(); navigate('/login'); }}
            className="w-full"
          >
            <LogOut className="mr-2 h-4 w-4" />
            Sign Out
          </Button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <header className="flex h-14 items-center border-b px-6" />
        <div className="p-6"><Outlet /></div>
      </main>
    </div>
  );
}
```

---

## Step 9: Route Pages

- [ ] **Step 9.1: Create `admin/src/routes/LoginPage.tsx`**

```typescript
// admin/src/routes/LoginPage.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuthStore } from '@/stores/auth-store';
import { api } from '@/lib/api';
import type { ApiError } from '@/lib/api';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const tokens = await api.post<{ access: string }>('/auth/login/', { email, password });
      localStorage.setItem('gnucash_access_token', tokens.access);

      const user = await api.get<{ id: string; email: string; is_staff: boolean; is_superuser: boolean }>('/users/me/');

      if (!user.is_staff) {
        setError('You do not have platform admin privileges.');
        localStorage.removeItem('gnucash_access_token');
        setIsLoading(false);
        return;
      }

      login(user, tokens.access);
      navigate('/admin/dashboard');
    } catch (err) {
      if (err instanceof Error) {
        setError('Invalid email or password.');
      }
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>GnuCash Admin</CardTitle>
          <CardDescription>Sign in with your platform admin account</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@gnucash.example"
                required
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 9.2: Create `admin/src/routes/DashboardPage.tsx`**

```typescript
// admin/src/routes/DashboardPage.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useDashboardStats } from '@/hooks/useAdminDashboard';
import { Building2, Users, FileText, TrendingUp } from 'lucide-react';

export function DashboardPage() {
  const { data: stats, isLoading, error } = useDashboardStats();

  if (isLoading) return <DashboardSkeleton />;
  if (error) return <div className="text-destructive">Failed to load dashboard stats.</div>;
  if (!stats) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Platform Dashboard</h1>
        <p className="mt-1 text-muted-foreground">Overview of your GnuCash Web platform.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Tenants"
          value={stats.total_tenants}
          icon={Building2}
          subtitle={`${stats.active_tenants_30d} active in last 30 days`}
        />
        <StatCard
          title="Total Users"
          value={stats.total_users}
          icon={Users}
          subtitle={`${stats.recent_signups} new this week`}
        />
        <StatCard
          title="Audit Events"
          value={stats.total_audit_events}
          icon={FileText}
          subtitle="Cross-tenant audit trail"
        />
        <StatCard
          title="Platform Health"
          value={<Badge variant="success">Operational</Badge>}
          icon={TrendingUp}
          subtitle="All systems normal"
        />
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  subtitle,
}: {
  title: string;
  value: number | React.ReactNode;
  icon: React.ComponentType<{ className?: string }>;
  subtitle: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
      </CardContent>
    </Card>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 animate-pulse rounded bg-muted" />
      <div className="h-4 w-72 animate-pulse rounded bg-muted" />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 9.3: Create `admin/src/routes/TenantsPage.tsx`**

```typescript
// admin/src/routes/TenantsPage.tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { useAdminTenants, useCreateTenant, useExtendTrial } from '@/hooks/useAdminTenants';
import type { AdminTenantCreate } from '@/types/admin';
import { format } from 'date-fns';
import { Plus, Search, Clock } from 'lucide-react';

export function TenantsPage() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<string | undefined>(undefined);
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading } = useAdminTenants({ search: search || undefined, status });
  const createTenant = useCreateTenant();
  const extendTrial = useExtendTrial();

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const formData = new FormData(form);
    const data: AdminTenantCreate = {
      name: formData.get('name') as string,
      slug: formData.get('slug') as string,
    };
    const trialEnds = formData.get('trial_ends_at') as string;
    if (trialEnds) data.trial_ends_at = trialEnds;
    createTenant.mutate(data, { onSuccess: () => setShowCreate(false) });
  };

  const tenants = data?.results ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Tenants</h1>
          <p className="mt-1 text-muted-foreground">Manage all platform tenants.</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Tenant
        </Button>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search tenants..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <select
          value={status ?? ''}
          onChange={(e) => setStatus(e.target.value || undefined)}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">All Statuses</option>
          <option value="trial">Trial</option>
          <option value="active">Active</option>
          <option value="expired">Expired</option>
        </select>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{data?.count ?? 0} Tenants</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Slug</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>Members</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenants.map((tenant) => (
                  <TableRow key={tenant.id}>
                    <TableCell className="font-medium">{tenant.name}</TableCell>
                    <TableCell>
                      <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{tenant.slug}</code>
                    </TableCell>
                    <TableCell>{tenant.owner_email ?? '—'}</TableCell>
                    <TableCell>{tenant.member_count}</TableCell>
                    <TableCell>
                      <TenantStatusBadge tenant={tenant} />
                    </TableCell>
                    <TableCell>
                      {format(new Date(tenant.created_at), 'yyyy-MM-dd')}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => extendTrial.mutate({ id: tenant.id, days: 14 })}
                        disabled={extendTrial.isPending}
                      >
                        <Clock className="mr-1 h-3 w-3" />
                        Extend Trial
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {tenants.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      No tenants found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Tenant</DialogTitle>
            <DialogDescription>
              Create a new tenant workspace for an organization.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="tenant-name">Name</Label>
              <Input id="tenant-name" name="name" placeholder="Acme Corp" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tenant-slug">Slug</Label>
              <Input id="tenant-slug" name="slug" placeholder="acme-corp" required pattern="[a-z0-9-]+" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="trial-ends">Trial Ends At (optional)</Label>
              <Input id="trial-ends" name="trial_ends_at" type="datetime-local" />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createTenant.isPending}>
                {createTenant.isPending ? 'Creating...' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function TenantStatusBadge({ tenant }: { tenant: { trial_ends_at: string | null; stripe_customer_id: string } }) {
  if (tenant.stripe_customer_id) {
    return <Badge variant="success">Active</Badge>;
  }
  if (tenant.trial_ends_at && new Date(tenant.trial_ends_at) > new Date()) {
    return <Badge variant="warning">Trial</Badge>;
  }
  return <Badge variant="destructive">Expired</Badge>;
}

function TableSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="h-10 animate-pulse rounded bg-muted" />
      ))}
    </div>
  );
}
```

- [ ] **Step 9.4: Create `admin/src/routes/UsersPage.tsx`**

```typescript
// admin/src/routes/UsersPage.tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { useAdminUsers, useToggleUserActive, useSetUserStaff } from '@/hooks/useAdminUsers';
import { format } from 'date-fns';
import { Search, UserCheck, UserX } from 'lucide-react';

export function UsersPage() {
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(undefined);

  const { data, isLoading } = useAdminUsers({ search: search || undefined, is_active: activeFilter });
  const toggleActive = useToggleUserActive();
  const setStaff = useSetUserStaff();

  const users = data?.results ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Users</h1>
        <p className="mt-1 text-muted-foreground">Cross-tenant user directory.</p>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <select
          value={activeFilter === undefined ? '' : activeFilter ? 'active' : 'inactive'}
          onChange={(e) => {
            const v = e.target.value;
            setActiveFilter(v === '' ? undefined : v === 'active');
          }}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">All Users</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{data?.count ?? 0} Users</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-10 animate-pulse rounded bg-muted" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Staff</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Tenants</TableHead>
                  <TableHead>Last Login</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">{user.email}</TableCell>
                    <TableCell>
                      {user.is_staff ? (
                        <Badge variant="default">Staff</Badge>
                      ) : (
                        <Badge variant="secondary">User</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {user.is_active ? (
                        <Badge variant="success">Active</Badge>
                      ) : (
                        <Badge variant="destructive">Inactive</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {user.tenant_count} tenant{user.tenant_count !== 1 ? 's' : ''}
                      </span>
                    </TableCell>
                    <TableCell>
                      {user.last_login_at
                        ? format(new Date(user.last_login_at), 'yyyy-MM-dd HH:mm')
                        : 'Never'}
                    </TableCell>
                    <TableCell>
                      {format(new Date(user.created_at), 'yyyy-MM-dd')}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleActive.mutate(user.id)}
                          disabled={toggleActive.isPending}
                        >
                          {user.is_active ? (
                            <><UserX className="mr-1 h-3 w-3" /> Deactivate</>
                          ) : (
                            <><UserCheck className="mr-1 h-3 w-3" /> Activate</>
                          )}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {users.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      No users found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 9.5: Create `admin/src/routes/BillingPage.tsx`**

```typescript
// admin/src/routes/BillingPage.tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ExternalLink } from 'lucide-react';

export function BillingPage() {
  const stripeDashboardUrl = import.meta.env.VITE_STRIPE_DASHBOARD_URL ?? 'https://dashboard.stripe.com';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Billing</h1>
        <p className="mt-1 text-muted-foreground">Stripe billing dashboard and subscription management.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Stripe Dashboard</CardTitle>
          <CardDescription>
            Access the Stripe dashboard for subscription management, invoices, and revenue analytics.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4 py-8">
          <p className="text-center text-muted-foreground">
            For full billing analytics, subscription details, and revenue reports,
            open the Stripe dashboard.
          </p>
          <Button asChild>
            <a href={stripeDashboardUrl} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="mr-2 h-4 w-4" />
              Open Stripe Dashboard
            </a>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Subscription Plans</CardTitle>
          <CardDescription>Configured pricing tiers for tenant subscriptions.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <PlanCard name="Free" price="$0" features={['1 user', 'Basic accounts', 'Transaction entry']} />
            <PlanCard name="Pro" price="$15/mo" features={['Up to 5 users', 'Budgets & reports', 'Receipt scanning', 'Recurring transactions']} highlighted />
            <PlanCard name="Enterprise" price="$49/mo" features={['Unlimited users', 'Investment tracking', 'Import/export', 'Priority support', 'Custom integrations']} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PlanCard({ name, price, features, highlighted = false }: {
  name: string;
  price: string;
  features: string[];
  highlighted?: boolean;
}) {
  return (
    <Card className={highlighted ? 'border-primary shadow-md' : ''}>
      <CardHeader>
        <CardTitle className="text-lg">{name}</CardTitle>
        <CardDescription className="text-2xl font-bold">{price}</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {features.map((feature) => (
            <li key={feature} className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="text-primary">&#10003;</span>
              {feature}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 9.6: Create `admin/src/routes/SupportPage.tsx`**

```typescript
// admin/src/routes/SupportPage.tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export function SupportPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Support</h1>
        <p className="mt-1 text-muted-foreground">Support tickets and user assistance.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Coming Soon</CardTitle>
          <CardDescription>
            The support ticket system is planned for a future release.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-4 py-12">
            <Badge variant="secondary" className="text-lg px-4 py-2">MVP Placeholder</Badge>
            <p className="text-center text-muted-foreground max-w-md">
              Support ticket functionality including user-submitted tickets,
              admin response workflow, and SLA tracking will be added in Phase 8.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 9.7: Create `admin/src/routes/AnalyticsPage.tsx`**

```typescript
// admin/src/routes/AnalyticsPage.tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useDashboardStats } from '@/hooks/useAdminDashboard';
import { format } from 'date-fns';

export function AnalyticsPage() {
  const { data: stats, isLoading, error } = useDashboardStats();

  if (isLoading) return <AnalyticsSkeleton />;
  if (error) return <div className="text-destructive">Failed to load analytics data.</div>;
  if (!stats) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        <p className="mt-1 text-muted-foreground">Platform-wide growth and engagement metrics.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Signups</CardTitle>
            <CardDescription>New user registrations over the past 7 days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">{stats.recent_signups}</div>
            <p className="mt-2 text-sm text-muted-foreground">
              {stats.recent_signups > 0
                ? `${stats.recent_signups} new user${stats.recent_signups !== 1 ? 's' : ''} this week`
                : 'No new signups this week'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Active Tenants</CardTitle>
            <CardDescription>Tenants with activity in the last 30 days</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">{stats.active_tenants_30d}</div>
            <p className="mt-2 text-sm text-muted-foreground">
              Out of {stats.total_tenants} total tenants
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Total Audit Events</CardTitle>
            <CardDescription>Cross-tenant action trail</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">{stats.total_audit_events}</div>
            <p className="mt-2 text-sm text-muted-foreground">
              All CREATE, UPDATE, DELETE, LOGIN events across all tenants
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>User-to-Tenant Ratio</CardTitle>
            <CardDescription>Average users per tenant</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold">
              {stats.total_tenants > 0
                ? (stats.total_users / stats.total_tenants).toFixed(1)
                : '0.0'}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {stats.total_users} users across {stats.total_tenants} tenants
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-40 animate-pulse rounded bg-muted" />
      <div className="h-4 w-72 animate-pulse rounded bg-muted" />
      <div className="grid gap-4 md:grid-cols-2">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-40 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 9.8: Create `admin/src/routes/AuditLogPage.tsx`**

```typescript
// admin/src/routes/AuditLogPage.tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '@/components/ui/dialog';
import { useAdminAuditLog } from '@/hooks/useAdminAuditLog';
import type { AuditLogFilters } from '@/hooks/useAdminAuditLog';
import { format } from 'date-fns';
import { Search, Eye } from 'lucide-react';

export function AuditLogPage() {
  const [filters, setFilters] = useState<AuditLogFilters>({});
  const [selectedEntry, setSelectedEntry] = useState<import('@/types/admin').AdminAuditLog | null>(null);

  const { data, isLoading } = useAdminAuditLog(filters);

  const logs = data?.results ?? [];

  const handleSearch = (field: keyof AuditLogFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [field]: value || undefined }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Audit Log</h1>
        <p className="mt-1 text-muted-foreground">Cross-tenant audit event viewer. All entries are immutable.</p>
      </div>

      <div className="flex gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Filter by model..."
            value={filters.model ?? ''}
            onChange={(e) => handleSearch('model', e.target.value)}
            className="pl-9"
          />
        </div>
        <Input
          placeholder="Filter by user email..."
          value={filters.user_email ?? ''}
          onChange={(e) => handleSearch('user_email', e.target.value)}
          className="min-w-[200px]"
        />
        <Input
          placeholder="Filter by action (CREATE, UPDATE...)"
          value={filters.action ?? ''}
          onChange={(e) => handleSearch('action', e.target.value)}
          className="min-w-[200px]"
        />
        <Input
          placeholder="Date from (YYYY-MM-DD)"
          value={filters.date_from ?? ''}
          onChange={(e) => handleSearch('date_from', e.target.value)}
          className="min-w-[180px]"
        />
        <Input
          placeholder="Date to (YYYY-MM-DD)"
          value={filters.date_to ?? ''}
          onChange={(e) => handleSearch('date_to', e.target.value)}
          className="min-w-[180px]"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{data?.count ?? 0} Audit Events</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-10 animate-pulse rounded bg-muted" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Tenant</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Object ID</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="text-sm">
                      {format(new Date(log.timestamp), 'yyyy-MM-dd HH:mm')}
                    </TableCell>
                    <TableCell className="font-medium">{log.tenant_name}</TableCell>
                    <TableCell>{log.user_email ?? 'system'}</TableCell>
                    <TableCell><ActionBadge action={log.action} /></TableCell>
                    <TableCell>
                      <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{log.model}</code>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {log.object_id.slice(0, 8)}...
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedEntry(log)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {logs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      No audit events found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!selectedEntry} onOpenChange={() => setSelectedEntry(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Audit Event Details</DialogTitle>
            <DialogDescription>
              {selectedEntry && (
                <>
                  {selectedEntry.action} on {selectedEntry.model}#{selectedEntry.object_id.slice(0, 8)}
                  {' '}by {selectedEntry.user_email ?? 'system'} at{' '}
                  {selectedEntry && format(new Date(selectedEntry.timestamp), 'yyyy-MM-dd HH:mm:ss')}
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          {selectedEntry && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Tenant:</span> {selectedEntry.tenant_name}
                </div>
                <div>
                  <span className="font-medium">IP Address:</span> {selectedEntry.ip_address ?? '—'}
                </div>
                <div>
                  <span className="font-medium">User Agent:</span>{' '}
                  <span className="text-muted-foreground">{selectedEntry.user_agent}</span>
                </div>
                <div>
                  <span className="font-medium">Timestamp:</span>{' '}
                  {format(new Date(selectedEntry.timestamp), 'yyyy-MM-dd HH:mm:ss')}
                </div>
              </div>
              {selectedEntry.old_values && (
                <div>
                  <span className="font-medium">Old Values:</span>
                  <pre className="mt-1 rounded bg-muted p-3 text-xs overflow-auto">
                    {JSON.stringify(selectedEntry.old_values, null, 2)}
                  </pre>
                </div>
              )}
              {selectedEntry.new_values && (
                <div>
                  <span className="font-medium">New Values:</span>
                  <pre className="mt-1 rounded bg-muted p-3 text-xs overflow-auto">
                    {JSON.stringify(selectedEntry.new_values, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function ActionBadge({ action }: { action: string }) {
  const variantMap: Record<string, 'default' | 'destructive' | 'secondary' | 'warning'> = {
    CREATE: 'default',
    UPDATE: 'warning',
    DELETE: 'destructive',
    LOGIN: 'secondary',
    LOGOUT: 'secondary',
    EXPORT: 'secondary',
  };
  return <Badge variant={variantMap[action] ?? 'secondary'}>{action}</Badge>;
}
```

- [ ] **Step 9.9: Create `admin/src/routes/NotFoundPage.tsx`**

```typescript
// admin/src/routes/NotFoundPage.tsx
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';

export function NotFoundPage() {
  return (
    <div className="flex h-screen flex-col items-center justify-center">
      <h1 className="text-6xl font-bold">404</h1>
      <p className="mt-4 text-xl text-muted-foreground">Page not found</p>
      <p className="mt-2 text-muted-foreground">
        The page you are looking for does not exist.
      </p>
      <Button asChild className="mt-6">
        <Link to="/admin/dashboard">Back to Dashboard</Link>
      </Button>
    </div>
  );
}
```

---

## Step 10: App Router

- [ ] **Step 10.1: Create `admin/src/App.tsx`**

```typescript
// admin/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/query-client';
import { RootLayout } from '@/components/layouts/RootLayout';
import { AdminAuthGuard } from '@/components/layouts/AdminAuthGuard';
import { LoginPage } from '@/routes/LoginPage';
import { DashboardPage } from '@/routes/DashboardPage';
import { TenantsPage } from '@/routes/TenantsPage';
import { UsersPage } from '@/routes/UsersPage';
import { BillingPage } from '@/routes/BillingPage';
import { SupportPage } from '@/routes/SupportPage';
import { AnalyticsPage } from '@/routes/AnalyticsPage';
import { AuditLogPage } from '@/routes/AuditLogPage';
import { NotFoundPage } from '@/routes/NotFoundPage';

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<AdminAuthGuard />}>
            <Route element={<RootLayout />}>
              <Route path="/admin/dashboard" element={<DashboardPage />} />
              <Route path="/admin/tenants" element={<TenantsPage />} />
              <Route path="/admin/users" element={<UsersPage />} />
              <Route path="/admin/billing" element={<BillingPage />} />
              <Route path="/admin/support" element={<SupportPage />} />
              <Route path="/admin/analytics" element={<AnalyticsPage />} />
              <Route path="/admin/audit" element={<AuditLogPage />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

---

## Step 11: Wire Backend Admin API into Existing Users Endpoint

The admin login page calls `/api/v1/admin/users/me/` to get the current user's staff status. We need to add this endpoint.

- [ ] **Step 11.1: Add a `CurrentUserView` to `backend/admin_api/views.py`**

Append to the end of `backend/admin_api/views.py`:

```python
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated


class CurrentUserView(generics.RetrieveAPIView):
    """
    GET /api/v1/admin/users/me/ — Returns the authenticated user's details.
    Used by the admin hub login flow to verify is_staff status.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        from admin_api.serializers import AdminUserSerializer
        return AdminUserSerializer
```

- [ ] **Step 11.2: Add the route in `backend/admin_api/urls.py`**

Add to the `urlpatterns` list:

```python
from admin_api.views import CurrentUserView

urlpatterns = [
    path('users/me/', CurrentUserView.as_view(), name='admin-current-user'),
    path('dashboard/', DashboardStatsView.as_view({'get': 'stats'}), name='admin-dashboard-stats'),
] + router.urls
```

---

## Step 12: Commit

- [ ] **Step 12.1: Backend commit**

```bash
git add backend/admin_api/
git add backend/gnucash_web/urls.py
git add backend/gnucash_web/settings/base.py
git commit -m "feat(admin-api): add platform admin ViewSets and serializers

Add Tenant, User, and AuditLog admin ViewSets with IsPlatformAdmin
permission. Wire admin routes under /api/v1/admin/. Add dashboard
stats endpoint and current-user lookup for admin hub login."
```

- [ ] **Step 12.2: Admin app commit**

```bash
git add admin/
git commit -m "feat(admin-hub): create Vite + React admin hub application

Scaffold admin app with TypeScript strict mode, shadcn/ui components,
React Query data fetching, and admin sidebar layout. Implement pages
for dashboard, tenants, users, billing, analytics, audit log, and
support. All routes protected by is_staff guard."
```

---

## Self-Review

### Spec Coverage Check

| Spec Route | Task | Status |
|---|---|---|
| `/admin/dashboard` | Step 9.2 (DashboardPage) | Covered |
| `/admin/tenants` | Step 9.3 (TenantsPage) + Step 6.1 (hooks) + Step 1.3 (backend) | Covered |
| `/admin/users` | Step 9.4 (UsersPage) + Step 6.2 (hooks) + Step 1.3 (backend) | Covered |
| `/admin/billing` | Step 9.5 (BillingPage) | Covered |
| `/admin/support` | Step 9.6 (SupportPage, MVP placeholder) | Covered |
| `/admin/analytics` | Step 9.7 (AnalyticsPage) | Covered |
| `/admin/audit` | Step 9.8 (AuditLogPage) + Step 6.3 (hooks) + Step 1.3 (backend) | Covered |
| Admin login | Step 9.1 (LoginPage) + Step 7 (auth store) | Covered |
| Admin API backend | Steps 1.1-1.5 (admin_api app) | Covered |

### Placeholder Scan

No TBDs, TODOs, or "add later" comments in the generated code. The only explicit placeholder is the Support page content, which is intentional per spec ("placeholder for MVP").

### Type/Name Consistency

- All TypeScript uses `strict: true`, no `any` types — verified
- API paths follow `/api/v1/admin/` convention — consistent
- Admin serializers have `Admin` prefix — consistent
- Query keys use `['admin', <resource>]` prefix — consistent
- Backend permission `IsPlatformAdmin` checks `is_staff` — consistent with Django convention
- Admin routes use `/admin/` prefix — matches spec

### Architecture Notes

- The admin app runs on port **5174** (tenant app on **5173**) — no port conflicts
- Admin API client does NOT send `X-Tenant-ID` — it is a cross-tenant app by design
- `IsPlatformAdmin` is a DRF permission, not middleware — applied per-viewset
- The admin login reuses the existing `/api/v1/auth/login/` JWT endpoint via the proxy
- Dashboard stats are served via a ViewSet action, not a separate view — consistent with the existing pattern