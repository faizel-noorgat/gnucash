# Phase 3: Frontend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the tenant-facing React frontend with Vite, TypeScript, Tailwind CSS, shadcn/ui, React Query, Zustand, React Hook Form, and Zod. Wire up JWT-authenticated API client, React Router v6, and a root layout with auth guard. Deliver login, register, and the AccountList page as the first functional route.

**Architecture:** Single-page application served as static files. All API calls go to `/api/v1/` on the same origin (proxied in dev via Vite). JWT access token stored in memory (not localStorage), refresh token in HttpOnly cookie (set by backend). The API client intercepts 401 responses, triggers a silent refresh, and retries the original request.

**Tech Stack:** Vite 6, React 19, TypeScript 5, Tailwind CSS 4, shadcn/ui, React Query 5, Zustand 5, React Router v7 (legacy-router compat), React Hook Form 7, Zod 3, Axios 1

---

## File Map

### Files to Create
- `frontend/package.json` — Project dependencies and scripts
- `frontend/tsconfig.json` — TypeScript compiler options
- `frontend/tsconfig.node.json` — Node/TSConfig for Vite
- `frontend/vite.config.ts` — Vite configuration with API proxy
- `frontend/index.html` — HTML entry point
- `frontend/src/main.tsx` — React app entry with providers
- `frontend/src/App.tsx` — Root router component
- `frontend/src/vite-env.d.ts` — Vite type declarations
- `frontend/src/index.css` — Tailwind directives + base styles
- `frontend/src/lib/api-client.ts` — Axios instance with JWT interceptor
- `frontend/src/lib/query-client.ts` — React Query client setup
- `frontend/src/hooks/use-auth.ts` — Auth state hook (Zustand store)
- `frontend/src/stores/auth-store.ts` — Auth Zustand store
- `frontend/src/components/layouts/RootLayout.tsx` — Shell layout with sidebar + auth guard
- `frontend/src/components/layouts/AuthLayout.tsx` — Centered card layout for login/register
- `frontend/src/components/ui/button.tsx` — shadcn Button
- `frontend/src/components/ui/input.tsx` — shadcn Input
- `frontend/src/components/ui/label.tsx` — shadcn Label
- `frontend/src/components/ui/card.tsx` — shadcn Card
- `frontend/src/routes/ProtectedRoute.tsx` — Auth guard wrapper
- `frontend/src/routes/LoginPage.tsx` — Login page
- `frontend/src/routes/RegisterPage.tsx` — Register page
- `frontend/src/routes/DashboardPage.tsx` — Placeholder dashboard
- `frontend/src/routes/AccountListPage.tsx` — Account list with data table
- `frontend/src/routes/NotFoundPage.tsx` — 404 fallback
- `frontend/tailwind.config.ts` — Tailwind configuration
- `frontend/postcss.config.js` — PostCSS configuration

### Files to Modify
- `.gitignore` — Already contains `frontend/dist/` and `frontend/node_modules/`

---

### Task 1: Project Scaffold and Configuration

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "gnucash-web-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint .",
    "typecheck": "tsc -b --noEmit"
  },
  "dependencies": {
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-slot": "^1.1.0",
    "@tanstack/react-query": "^5.62.0",
    "@tanstack/react-table": "^8.20.5",
    "axios": "^1.7.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.0",
    "lucide-react": "^0.460.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-hook-form": "^7.54.0",
    "react-router-dom": "^7.0.0",
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

- [ ] **Step 2: Create tsconfig.json**

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
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: Create tsconfig.node.json**

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
    "noEmit": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Create vite.config.ts**

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 5: Create index.html**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>GnuCash Web</title>
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Create tailwind.config.ts**

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
        primary: {
          DEFAULT: 'hsl(222.2 47.4% 11.2%)',
          foreground: 'hsl(210 40% 98%)',
        },
        secondary: {
          DEFAULT: 'hsl(210 40% 96.1%)',
          foreground: 'hsl(222.2 47.4% 11.2%)',
        },
        destructive: {
          DEFAULT: 'hsl(0 84.2% 60.2%)',
          foreground: 'hsl(210 40% 98%)',
        },
        muted: {
          DEFAULT: 'hsl(210 40% 96.1%)',
          foreground: 'hsl(215.4 16.3% 46.9%)',
        },
        accent: {
          DEFAULT: 'hsl(210 40% 96.1%)',
          foreground: 'hsl(222.2 47.4% 11.2%)',
        },
        popover: {
          DEFAULT: 'hsl(0 0% 100%)',
          foreground: 'hsl(222.2 84% 4.9%)',
        },
        card: {
          DEFAULT: 'hsl(0 0% 100%)',
          foreground: 'hsl(222.2 84% 4.9%)',
        },
      },
      borderRadius: {
        lg: '0.5rem',
        md: 'calc(0.5rem - 2px)',
        sm: 'calc(0.5rem - 4px)',
      },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 7: Create postcss.config.js**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 8: Create vite-env.d.ts**

```typescript
/// <reference types="vite/client" />
```

- [ ] **Step 9: Create src/index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  }
}
```

- [ ] **Step 10: Install dependencies and verify**

```bash
cd frontend && npm install
```

- [ ] **Step 11: Verify dev server starts**

```bash
cd frontend && npm run dev
```

Expected: Vite starts on `http://localhost:5173` with no errors.

- [ ] **Step 12: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold frontend with Vite, React, TypeScript, Tailwind"
```

---

### Task 2: shadcn/ui Base Components

**Files:**
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/input.tsx`
- Create: `frontend/src/components/ui/label.tsx`
- Create: `frontend/src/components/ui/card.tsx`

- [ ] **Step 1: Create cn() utility**

```typescript
// frontend/src/lib/utils.ts
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: Create Button component**

```typescript
// frontend/src/components/ui/button.tsx
import { Slot } from '@radix-ui/react-slot';
import { type VariantProps, cva } from 'class-variance-authority';
import * as React from 'react';

import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = 'Button';

export { Button, buttonVariants };
```

- [ ] **Step 3: Create Input component**

```typescript
// frontend/src/components/ui/input.tsx
import * as React from 'react';

import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Input.displayName = 'Input';

export { Input };
```

- [ ] **Step 4: Create Label component**

```typescript
// frontend/src/components/ui/label.tsx
import * as LabelPrimitive from '@radix-ui/react-label';
import { type VariantProps, cva } from 'class-variance-authority';
import * as React from 'react';

import { cn } from '@/lib/utils';

const labelVariants = cva(
  'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
);

const Label = React.forwardRef<
  React.ComponentRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> & VariantProps<typeof labelVariants>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn(labelVariants(), className)}
    {...props}
  />
));
Label.displayName = LabelPrimitive.Root.displayName;

export { Label };
```

- [ ] **Step 5: Create Card component**

```typescript
// frontend/src/components/ui/card.tsx
import * as React from 'react';

import { cn } from '@/lib/utils';

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('rounded-lg border bg-card text-card-foreground shadow-sm', className)}
      {...props}
    />
  ),
);
Card.displayName = 'Card';

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />
  ),
);
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn('text-2xl font-semibold leading-none tracking-tight', className)}
      {...props}
    />
  ),
);
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p ref={ref} className={cn('text-sm text-muted-foreground', className)} {...props} />
));
CardDescription.displayName = 'CardDescription';

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
  ),
);
CardContent.displayName = 'CardContent';

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center p-6 pt-0', className)} {...props} />
  ),
);
CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/utils.ts frontend/src/components/ui/
git commit -m "feat: add shadcn/ui base components (button, input, label, card)"
```

---

### Task 3: API Client with JWT Auth Interceptor

**Files:**
- Create: `frontend/src/lib/api-client.ts`
- Create: `frontend/src/lib/query-client.ts`

- [ ] **Step 1: Create the Axios API client with refresh logic**

The backend returns `{access, refresh}` on login. The refresh endpoint `POST /api/v1/auth/refresh/` accepts `{refresh: "<token>"}` and returns `{access: "<new_token>"}`. The refresh token is stored in an HttpOnly cookie set by the backend, so the refresh request does not need to send it explicitly -- the cookie is sent automatically by the browser.

```typescript
// frontend/src/lib/api-client.ts
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Sends HttpOnly cookies (refresh token) cross-origin
});

// In-memory access token -- never persisted to localStorage
let accessToken: string | null = null;

// Flag to prevent concurrent refresh attempts
let isRefreshing = false;
type RefreshSubscriber = (token: string | null) => void;
let refreshSubscribers: RefreshSubscriber[] = [];

const onRefreshed = (token: string | null) => {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
};

const addRefreshSubscriber = (cb: RefreshSubscriber) => {
  refreshSubscribers.push(cb);
};

// Request interceptor: attach access token if available
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// Response interceptor: handle 401 with token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (isRefreshing) {
        // Another refresh is in flight -- queue this request
        return new Promise((resolve) => {
          addRefreshSubscriber((token) => {
            if (token) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            resolve(api(originalRequest));
          });
        });
      }

      isRefreshing = true;

      try {
        const response = await axios.post<{ access: string }>(
          '/api/v1/auth/refresh/',
          {},
          { withCredentials: true },
        );
        accessToken = response.data.access;
        isRefreshing = false;
        onRefreshed(accessToken);

        originalRequest.headers.Authorization = `Bearer ${accessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed -- clear token and redirect to login
        accessToken = null;
        isRefreshing = false;
        onRefreshed(null);
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);

// Export helper to set token after login
export const setAccessToken = (token: string) => {
  accessToken = token;
};

export const getAccessToken = () => accessToken;

export const clearAccessToken = () => {
  accessToken = null;
};

export default api;
```

- [ ] **Step 2: Create React Query client**

```typescript
// frontend/src/lib/query-client.ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors
        if (error?.response?.status && error.response.status >= 400 && error.response.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
    },
  },
});
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api-client.ts frontend/src/lib/query-client.ts
git commit -m "feat: add authenticated API client with JWT refresh interceptor"
```

---

### Task 4: Auth State with Zustand

**Files:**
- Create: `frontend/src/stores/auth-store.ts`
- Create: `frontend/src/hooks/use-auth.ts`

- [ ] **Step 1: Create Zustand auth store**

The store holds the authenticated user profile and tenant ID. It does NOT persist to localStorage -- session is restored by checking for an existing access token cookie or by re-login. The tenant ID is stored in localStorage so it survives page refresh (tenant selection is a user preference, not secret data).

```typescript
// frontend/src/stores/auth-store.ts
import { create } from 'zustand';

import { clearAccessToken, setAccessToken } from '@/lib/api-client';

export interface User {
  id: string;
  email: string;
}

interface AuthState {
  user: User | null;
  tenantId: string | null;
  isLoading: boolean;

  login: (user: User, accessToken: string, tenantId: string) => void;
  setTenantId: (tenantId: string) => void;
  logout: () => void;
  setLoading: (isLoading: boolean) => void;
}

const TENANT_ID_STORAGE_KEY = 'gnucash_tenant_id';

const getStoredTenantId = (): string | null => {
  try {
    return localStorage.getItem(TENANT_ID_STORAGE_KEY);
  } catch {
    return null;
  }
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  tenantId: getStoredTenantId(),
  isLoading: false,

  login: (user, token, tenantId) => {
    setAccessToken(token);
    localStorage.setItem(TENANT_ID_STORAGE_KEY, tenantId);
    set({ user, tenantId });
  },

  setTenantId: (tenantId) => {
    localStorage.setItem(TENANT_ID_STORAGE_KEY, tenantId);
    set({ tenantId });
  },

  logout: () => {
    clearAccessToken();
    try {
      localStorage.removeItem(TENANT_ID_STORAGE_KEY);
    } catch {
      // Ignore
    }
    set({ user: null, tenantId: null });
  },

  setLoading: (isLoading) => set({ isLoading }),
}));
```

- [ ] **Step 2: Create useAuth convenience hook**

```typescript
// frontend/src/hooks/use-auth.ts
import { useAuthStore } from '@/stores/auth-store';

export function useAuth() {
  const user = useAuthStore((state) => state.user);
  const tenantId = useAuthStore((state) => state.tenantId);
  const isLoading = useAuthStore((state) => state.isLoading);
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);
  const setTenantId = useAuthStore((state) => state.setTenantId);

  const isAuthenticated = user !== null;

  return {
    user,
    tenantId,
    isLoading,
    isAuthenticated,
    login,
    logout,
    setTenantId,
  };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/auth-store.ts frontend/src/hooks/use-auth.ts
git commit -m "feat: add Zustand auth store with tenant ID persistence"
```

---

### Task 5: Routing and Layouts

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/components/layouts/RootLayout.tsx`
- Create: `frontend/src/components/layouts/AuthLayout.tsx`
- Create: `frontend/src/routes/ProtectedRoute.tsx`
- Create: `frontend/src/routes/LoginPage.tsx`
- Create: `frontend/src/routes/RegisterPage.tsx`
- Create: `frontend/src/routes/DashboardPage.tsx`
- Create: `frontend/src/routes/NotFoundPage.tsx`

- [ ] **Step 1: Create ProtectedRoute guard**

```typescript
// frontend/src/routes/ProtectedRoute.tsx
import { Navigate, Outlet } from 'react-router-dom';

import { useAuth } from '@/hooks/use-auth';

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
```

- [ ] **Step 2: Create AuthLayout (centered card for login/register)**

```typescript
// frontend/src/components/layouts/AuthLayout.tsx
import { Outlet } from 'react-router-dom';

export function AuthLayout() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50 px-4">
      <div className="w-full max-w-md">
        <Outlet />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create RootLayout (app shell with sidebar)**

```typescript
// frontend/src/components/layouts/RootLayout.tsx
import { Outlet, useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/use-auth';

const navItems = [
  { label: 'Dashboard', path: '/' },
  { label: 'Accounts', path: '/accounts' },
  { label: 'Transactions', path: '/transactions' },
  { label: 'Budgets', path: '/budgets' },
  { label: 'Investments', path: '/investments' },
  { label: 'Receipts', path: '/receipts' },
  { label: 'Recurring', path: '/recurring' },
  { label: 'Reports', path: '/reports' },
  { label: 'Settings', path: '/settings' },
];

export function RootLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r bg-card">
        <div className="flex h-14 items-center border-b px-6">
          <h1 className="text-lg font-semibold">GnuCash Web</h1>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className="flex w-full items-center rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="border-t px-3 py-4">
          <div className="mb-2 px-3 text-xs text-muted-foreground">{user?.email}</div>
          <Button variant="outline" size="sm" onClick={handleLogout} className="w-full">
            Sign Out
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <header className="flex h-14 items-center border-b px-6" />
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Create LoginPage**

```typescript
// frontend/src/routes/LoginPage.tsx
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate, Link } from 'react-router-dom';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks/use-auth';
import api from '@/lib/api-client';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});

type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const { login, setLoading } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    setError(null);
    setLoading(true);
    try {
      const response = await api.post<{ access: string; user: { id: string; email: string } }>(
        '/auth/login/',
        data,
      );
      // The backend sets the refresh token in an HttpOnly cookie automatically.
      // We store the access token in memory and persist the tenant ID.
      // For MVP, assume the login response includes the user's first tenant ID.
      // If not, fetch it separately.
      const tenantId = response.data.user.id; // Placeholder -- adjust based on actual API response
      login(response.data.user, response.data.access, tenantId);
      navigate('/');
    } catch (err: any) {
      if (err.response?.status === 401) {
        setError('Invalid email or password.');
      } else {
        setError('Login failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl">Sign In</CardTitle>
        <CardDescription>Enter your email and password to access your account.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" placeholder="you@example.com" {...register('email')} />
            {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" {...register('password')} />
            {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary underline-offset-4 hover:underline">
              Create one
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 5: Create RegisterPage**

```typescript
// frontend/src/routes/RegisterPage.tsx
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate, Link } from 'react-router-dom';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import api from '@/lib/api-client';

const registerSchema = z
  .object({
    email: z.string().email('Invalid email address'),
    password: z
      .string()
      .min(12, 'Password must be at least 12 characters')
      .regex(/[A-Z]/, 'Password must contain an uppercase letter')
      .regex(/[a-z]/, 'Password must contain a lowercase letter')
      .regex(/[0-9]/, 'Password must contain a digit'),
    tenant_name: z.string().min(1, 'Tenant name is required'),
    tenant_slug: z.string().min(1, 'Tenant slug is required').regex(/^[a-z0-9-]+$/, 'Slug must be lowercase letters, numbers, and hyphens'),
  });

type RegisterForm = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterForm) => {
    setError(null);
    try {
      await api.post('/auth/register/', data);
      // After successful registration, redirect to login
      navigate('/login');
    } catch (err: any) {
      if (err.response?.data) {
        const detail = err.response.data.detail || err.response.data;
        setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
      } else {
        setError('Registration failed. Please try again.');
      }
    }
  };

  return (
    <Card>
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl">Create Account</CardTitle>
        <CardDescription>Set up your GnuCash Web household workspace.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" placeholder="you@example.com" {...register('email')} />
            {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" {...register('password')} />
            {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="tenant_name">Household Name</Label>
            <Input id="tenant_name" placeholder="My Household" {...register('tenant_name')} />
            {errors.tenant_name && <p className="text-sm text-destructive">{errors.tenant_name.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="tenant_slug">URL Slug</Label>
            <Input id="tenant_slug" placeholder="my-household" {...register('tenant_slug')} />
            {errors.tenant_slug && <p className="text-sm text-destructive">{errors.tenant_slug.message}</p>}
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Creating account...' : 'Create Account'}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link to="/login" className="text-primary underline-offset-4 hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 6: Create DashboardPage (placeholder)**

```typescript
// frontend/src/routes/DashboardPage.tsx
export function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="mt-2 text-muted-foreground">Welcome to GnuCash Web. Select a section from the sidebar to get started.</p>
    </div>
  );
}
```

- [ ] **Step 7: Create NotFoundPage**

```typescript
// frontend/src/routes/NotFoundPage.tsx
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/button';

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <h1 className="text-6xl font-bold text-muted-foreground">404</h1>
      <p className="mt-4 text-lg text-muted-foreground">Page not found.</p>
      <Button asChild className="mt-6">
        <Link to="/">Go Home</Link>
      </Button>
    </div>
  );
}
```

- [ ] **Step 8: Create App.tsx with routes**

```typescript
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import { AuthLayout } from '@/components/layouts/AuthLayout';
import { RootLayout } from '@/components/layouts/RootLayout';
import { ProtectedRoute } from '@/routes/ProtectedRoute';
import { DashboardPage } from '@/routes/DashboardPage';
import { LoginPage } from '@/routes/LoginPage';
import { NotFoundPage } from '@/routes/NotFoundPage';
import { RegisterPage } from '@/routes/RegisterPage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public auth routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        {/* Protected tenant routes */}
        <Route element={<ProtectedRoute />}>
          <Route element={<RootLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/accounts" element={<AccountListPagePlaceholder />} />
            <Route path="/transactions" element={<PlaceholderPage title="Transactions" />} />
            <Route path="/budgets" element={<PlaceholderPage title="Budgets" />} />
            <Route path="/investments" element={<PlaceholderPage title="Investments" />} />
            <Route path="/receipts" element={<PlaceholderPage title="Receipts" />} />
            <Route path="/recurring" element={<PlaceholderPage title="Recurring" />} />
            <Route path="/reports" element={<PlaceholderPage title="Reports" />} />
            <Route path="/settings" element={<PlaceholderPage title="Settings" />} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div>
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="mt-2 text-muted-foreground">Coming soon.</p>
    </div>
  );
}

function AccountListPagePlaceholder() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Accounts</h1>
      <p className="mt-2 text-muted-foreground">Account list will appear here.</p>
    </div>
  );
}
```

Note: The `AccountListPage` and its imports will be added in Task 7. For this task, we use a placeholder. After Task 7, update the import at the top of this file:

```typescript
// After Task 7, add this import:
import { AccountListPage } from '@/routes/AccountListPage';
```

And replace the `AccountListPagePlaceholder` component reference with `AccountListPage`.

- [ ] **Step 9: Create main.tsx**

```typescript
// frontend/src/main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';

import { App } from '@/App';
import { queryClient } from '@/lib/query-client';
import '@/index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
```

- [ ] **Step 10: Verify routing works**

```bash
cd frontend && npm run dev
```

Navigate to `http://localhost:5173/login` -- the login form should render. Navigate to `http://localhost:5173/` -- should redirect to `/login`. Navigate to `http://localhost:5173/register` -- the registration form should render.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/App.tsx frontend/src/main.tsx frontend/src/components/layouts/ frontend/src/routes/ProtectedRoute.tsx frontend/src/routes/LoginPage.tsx frontend/src/routes/RegisterPage.tsx frontend/src/routes/DashboardPage.tsx frontend/src/routes/NotFoundPage.tsx
git commit -m "feat: add routing, auth layouts, login/register pages, and auth guard"
```

---

### Task 6: API Client Tenant Header Interceptor

**Files:**
- Modify: `frontend/src/lib/api-client.ts`

- [ ] **Step 1: Add X-Tenant-ID header to all requests**

All authenticated API requests must include the `X-Tenant-ID` header. The tenant ID is stored in the Zustand auth store. Add an interceptor that reads it on every request.

Add to `frontend/src/lib/api-client.ts`, after the existing request interceptor:

```typescript
// Add this import at the top:
import { getAccessToken } from './api-client';

// Modify the request interceptor to also set X-Tenant-ID:
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  // Read tenant ID from localStorage for each request
  try {
    const tenantId = localStorage.getItem('gnucash_tenant_id');
    if (tenantId) {
      config.headers['X-Tenant-ID'] = tenantId;
    }
  } catch {
    // Ignore localStorage errors
  }

  return config;
});
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/api-client.ts
git commit -m "feat: attach X-Tenant-ID header to all authenticated requests"
```

---

### Task 7: Account List Page with React Query

**Files:**
- Create: `frontend/src/routes/AccountListPage.tsx`
- Create: `frontend/src/hooks/use-accounts.ts`
- Modify: `frontend/src/App.tsx` -- wire real AccountListPage

- [ ] **Step 1: Create useAccounts hook**

```typescript
// frontend/src/hooks/use-accounts.ts
import { useQuery } from '@tanstack/react-query';

import api from '@/lib/api-client';

export interface Account {
  id: string;
  name: string;
  full_name: string;
  code: string | null;
  description: string | null;
  account_type: string;
  hidden: boolean;
  placeholder: boolean;
  created_at: string;
  updated_at: string;
}

interface AccountsResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Account[];
}

export function useAccounts() {
  return useQuery({
    queryKey: ['accounts'],
    queryFn: async () => {
      const { data } = await api.get<AccountsResponse>('/accounts/');
      return data;
    },
  });
}
```

- [ ] **Step 2: Create AccountListPage**

```typescript
// frontend/src/routes/AccountListPage.tsx
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAccounts } from '@/hooks/use-accounts';

export function AccountListPage() {
  const { data, isLoading, error } = useAccounts();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded bg-muted" />
        <div className="h-10 w-full animate-pulse rounded bg-muted" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 w-full animate-pulse rounded bg-muted" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4">
        <p className="text-sm text-destructive">Failed to load accounts. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Accounts</h1>
        <Button asChild>
          <Link to="/accounts/new">New Account</Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{data?.count ?? 0} Accounts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Name</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Type</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Code</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Description</th>
                  <th className="w-24" />
                </tr>
              </thead>
              <tbody>
                {data?.results.map((account) => (
                  <tr key={account.id} className="border-b last:border-0">
                    <td className="px-4 py-3 text-sm font-medium">{account.full_name}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{account.account_type}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{account.code ?? '-'}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{account.description ?? '-'}</td>
                    <td className="px-4 py-3 text-right">
                      <Button variant="ghost" size="sm" asChild>
                        <Link to={`/accounts/${account.id}`}>View</Link>
                      </Button>
                    </td>
                  </tr>
                ))}
                {data?.results.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-sm text-muted-foreground">
                      No accounts yet. Create your first account to get started.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Wire AccountListPage into App.tsx**

Update `frontend/src/App.tsx`:

1. Add the import:
```typescript
import { AccountListPage } from '@/routes/AccountListPage';
```

2. Replace the placeholder route:
```typescript
// Change this line:
<Route path="/accounts" element={<AccountListPagePlaceholder />} />
// To this:
<Route path="/accounts" element={<AccountListPage />} />
```

3. Remove the `AccountListPagePlaceholder` function definition from the bottom of the file.

- [ ] **Step 4: Verify end-to-end**

1. Start the backend server:
```bash
cd backend && python manage.py runserver --settings=gnucash_web.settings.dev
```

2. Start the frontend dev server:
```bash
cd frontend && npm run dev
```

3. Register a new user at `http://localhost:5173/register`.
4. The app should redirect to `/login` after registration.
5. Log in at `http://localhost:5173/login`.
6. Navigate to `http://localhost:5173/accounts` -- the accounts table should load (empty if no accounts exist yet).
7. The Vite proxy forwards `/api/v1/*` to `http://localhost:8000`.
8. The `Authorization` header and `X-Tenant-ID` header should be attached to all API requests (verify in browser DevTools Network tab).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/AccountListPage.tsx frontend/src/hooks/use-accounts.ts frontend/src/App.tsx
git commit -m "feat: add AccountList page with React Query data fetching"
```

---

## Self-Review

### 1. Spec Coverage Check

| Spec Route | Task | Status |
|---|---|---|
| `/login` | Task 5 (LoginPage) | Covered |
| `/register` | Task 5 (RegisterPage) | Covered |
| `/` (Dashboard) | Task 5 (DashboardPage) | Covered |
| `/accounts` | Task 7 (AccountListPage) | Covered |
| All other routes | Task 5 (placeholder routes) | Stubbed, ready for future phases |

| Infrastructure | Task | Status |
|---|---|---|
| Vite + React + TypeScript | Task 1 | Covered |
| Tailwind CSS | Task 1 | Covered |
| shadcn/ui (button, input, label, card) | Task 2 | Covered |
| React Query setup | Task 3 (query-client), Task 7 (use-accounts) | Covered |
| Zustand auth store | Task 4 | Covered |
| React Hook Form + Zod | Task 5 (Login, Register) | Covered |
| API client with JWT interceptor | Task 3, Task 6 | Covered |
| React Router v7 routing | Task 5 | Covered |
| Auth guard (ProtectedRoute) | Task 5 | Covered |
| Root layout with sidebar | Task 5 (RootLayout) | Covered |
| Tenant header (`X-Tenant-ID`) | Task 6 | Covered |

### 2. Placeholder Scan

- `AccountListPage` links to `/accounts/new` and `/accounts/:id` -- these routes are not yet implemented (intentional, scoped to foundation only)
- DashboardPage is a placeholder -- intentional, full dashboard comes in a later phase
- All other protected routes render `PlaceholderPage` -- intentional, foundation scope
- The login flow assumes the backend returns a `user` object in the login response -- may need adjustment to match actual backend response shape

### 3. Security Checklist

- Access token stored in memory only (not localStorage/sessionStorage) -- covered
- Refresh token in HttpOnly cookie (set by backend, `withCredentials: true`) -- covered
- `X-Tenant-ID` read from localStorage (not secret, just a routing preference) -- covered
- 401 interceptor prevents stale token usage -- covered
- Concurrent refresh requests are queued (race condition protection) -- covered
- Form validation on client (Zod schema) -- covered, but server validation is authoritative

### 4. Type/Name Consistency

- All API response types use explicit TypeScript interfaces
- Query keys follow `['accounts']` pattern per frontend-state rules
- Route paths match the design spec exactly
- shadcn/ui components use `cn()` utility with `tailwind-merge` and `clsx`
- All components use `React.forwardRef` where appropriate for shadcn compatibility
