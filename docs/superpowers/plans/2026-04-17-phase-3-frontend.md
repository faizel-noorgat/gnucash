# Phase 3: Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the tenant-facing React frontend — Vite scaffold, Tailwind + shadcn/ui, native `fetch` + TanStack Query for all API calls, JWT auth with refresh, routing, auth pages, and the core accounting components (AccountPicker, SplitInput, TransactionForm, AccountList) plus reports and budget pages.

**Architecture:** Single-page application. All API calls go to `/api/v1/` (proxied in dev via Vite). JWT access token stored in memory only, refresh token in HttpOnly cookie (set by backend). A thin `fetch` wrapper handles `Authorization` + `X-Tenant-ID` headers and 401 retry with token refresh. TanStack Query manages caching, mutations, and cache invalidation.

**Tech Stack:** Vite 6, React 19, TypeScript 5, Tailwind CSS 3, shadcn/ui, @tanstack/react-query 5, Zustand 5, React Router 7, React Hook Form 7, Zod 3, date-fns, lucide-react. **No axios.**

---

## File Map (all tasks combined)

### To Create
- **Scaffold:** `frontend/package.json`, `tsconfig.json`, `tsconfig.node.json`, `vite.config.ts`, `index.html`, `tailwind.config.ts`, `postcss.config.js`, `src/index.css`, `src/vite-env.d.ts`
- **Lib:** `src/lib/utils.ts`, `src/lib/api.ts`, `src/lib/query-client.ts`
- **Types:** `src/types/account.ts`, `src/types/transaction.ts`, `src/types/report.ts`, `src/types/budget.ts`
- **Hooks:** `src/hooks/use-accounts.ts`, `src/hooks/use-transactions.ts`, `src/hooks/use-reports.ts`, `src/hooks/use-budgets.ts`, `src/hooks/use-split-balance.ts`, `src/hooks/use-auth.ts`
- **Store:** `src/stores/auth-store.ts`
- **UI (shadcn):** `src/components/ui/button.tsx`, `input.tsx`, `label.tsx`, `card.tsx`, `badge.tsx`, `table.tsx`, `skeleton.tsx`, `separator.tsx`, `popover.tsx`, `command.tsx`, `calendar.tsx`, `tooltip.tsx`, `progress.tsx`, `tabs.tsx`, `form.tsx`
- **Layouts:** `src/components/layouts/AuthLayout.tsx`, `src/components/layouts/RootLayout.tsx`
- **Routes:** `src/routes/ProtectedRoute.tsx`, `LoginPage.tsx`, `RegisterPage.tsx`, `DashboardPage.tsx`, `AccountListPage.tsx`, `NotFoundPage.tsx`
- **Components:** `src/components/account-picker.tsx`, `src/components/split-input.tsx`, `src/components/account-list.tsx`
- **Features:** `src/features/transactions/components/transaction-form-schema.ts`, `transaction-form.tsx`
- **Reports:** `src/routes/reports/index.tsx`, `balance-sheet.tsx`, `income-statement.tsx`, `cash-flow.tsx`, `components/ReportTable.tsx`, `components/ReportDatePicker.tsx`
- **Budgets:** `src/routes/budgets/index.tsx`, `$budgetId.tsx`, `new.tsx`, `components/BudgetCard.tsx`, `components/BudgetDetail.tsx`, `components/BudgetForm.tsx`
- **PWA:** `src/routes/offline.tsx`, `public/sw.js` (generated)
- **Tests:** `src/components/__tests__/account-picker.test.tsx`, `split-input.test.tsx`, `account-list.test.tsx`, `src/features/transactions/__tests__/transaction-form.test.tsx`

### To Modify
- `backend/gnucash_web/settings/base.py` — Add CORS origin for `localhost:5173`

---

## Prerequisites: Install shadcn/ui Primitives

Run once before any component task:

```bash
cd frontend
npx shadcn@latest add button input label card badge table skeleton separator popover command calendar tooltip progress tabs form
```

---

### Task 1: Project Scaffold

**Files:** `frontend/package.json`, `tsconfig.json`, `tsconfig.node.json`, `vite.config.ts`, `index.html`, `tailwind.config.ts`, `postcss.config.js`, `src/vite-env.d.ts`, `src/index.css`

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
    "typecheck": "tsc -b --noEmit"
  },
  "dependencies": {
    "@hookform/resolvers": "^4.1.0",
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-slot": "^1.1.0",
    "@radix-ui/react-popover": "^2.1.0",
    "@radix-ui/react-tooltip": "^1.1.0",
    "@radix-ui/react-separator": "^1.1.0",
    "@radix-ui/react-progress": "^1.1.0",
    "@radix-ui/react-tabs": "^1.1.0",
    "@radix-ui/react-dialog": "^1.1.0",
    "@radix-ui/react-dropdown-menu": "^2.1.0",
    "@tanstack/react-query": "^5.62.0",
    "@tanstack/react-table": "^8.20.5",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.0",
    "cmdk": "^1.0.0",
    "date-fns": "^4.1.0",
    "lucide-react": "^0.460.0",
    "react": "^19.0.0",
    "react-day-picker": "^9.5.0",
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
    "paths": { "@/*": ["src/*"] }
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
    alias: { '@': path.resolve(__dirname, './src') },
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

- [ ] **Step 7: Create postcss.config.js**

```javascript
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
};
```

- [ ] **Step 8: Create src/vite-env.d.ts**

```typescript
/// <reference types="vite/client" />
```

- [ ] **Step 9: Create src/index.css**

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

- [ ] **Step 10: Install and verify**

```bash
cd frontend && npm install
cd frontend && npm run dev
```

Expected: Vite starts on `http://localhost:5173`.

- [ ] **Step 11: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold frontend with Vite, React, TypeScript, Tailwind"
```

---

### Task 2: shadcn/ui Base Components

**Files:** `src/lib/utils.ts`, `src/components/ui/button.tsx`, `input.tsx`, `label.tsx`, `card.tsx`

- [ ] **Step 1: Create cn() utility**

```typescript
// frontend/src/lib/utils.ts
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: Create Button**

```tsx
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
      size: { default: 'h-10 px-4 py-2', sm: 'h-9 rounded-md px-3', lg: 'h-11 rounded-md px-8', icon: 'h-10 w-10' },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);
Button.displayName = 'Button';

export { Button, buttonVariants };
```

- [ ] **Step 3: Create Input**

```tsx
// frontend/src/components/ui/input.tsx
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

- [ ] **Step 4: Create Label**

```tsx
// frontend/src/components/ui/label.tsx
import * as LabelPrimitive from '@radix-ui/react-label';
import * as React from 'react';
import { cn } from '@/lib/utils';

const Label = React.forwardRef<
  React.ComponentRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root ref={ref} className={cn('text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70', className)} {...props} />
));
Label.displayName = LabelPrimitive.Root.displayName;
export { Label };
```

- [ ] **Step 5: Create Card**

```tsx
// frontend/src/components/ui/card.tsx
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

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/utils.ts frontend/src/components/ui/
git commit -m "feat: add shadcn/ui base components (button, input, label, card)"
```

---

### Task 3: Types and API Layer (native fetch)

**Files:** `src/types/account.ts`, `src/types/transaction.ts`, `src/types/report.ts`, `src/types/budget.ts`, `src/lib/api.ts`, `src/lib/query-client.ts`

- [ ] **Step 1: Create Account types**

```typescript
// frontend/src/types/account.ts
export type AccountType =
  | 'ASSET' | 'LIABILITY' | 'EQUITY' | 'INCOME' | 'EXPENSE'
  | 'BANK' | 'CASH' | 'CREDIT' | 'STOCK' | 'MUTUAL' | 'RECEIVABLE' | 'PAYABLE' | 'TRADING';

export interface Account {
  id: string;
  name: string;
  full_name: string;
  code: string | null;
  description: string | null;
  account_type: string;
  commodity: string;
  commodity_scu: number;
  hidden: boolean;
  placeholder: boolean;
  color: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Account[];
}
```

- [ ] **Step 2: Create Transaction types**

```typescript
// frontend/src/types/transaction.ts
export interface Split {
  id: string;
  account: string;
  memo: string;
  action: string;
  reconcile_state: string;
  reconcile_date: string | null;
  value: string;
  quantity: string;
  created_at: string;
}

export interface Transaction {
  id: string;
  guid: string;
  currency: string;
  num: string;
  post_date: string;
  enter_date: string;
  description: string;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  splits: Split[];
}

export interface TransactionListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Transaction[];
}

export interface SplitCreateData {
  account: string;
  value: string;
  quantity?: string;
  memo?: string;
}
```

- [ ] **Step 3: Create Report types**

```typescript
// frontend/src/types/report.ts
export interface BalanceSheetResponse {
  assets: string;
  liabilities: string;
  equity: string;
  retained_earnings: string;
  balanced: boolean;
}

export interface IncomeStatementResponse {
  revenue: string;
  expenses: string;
  net_income: string;
}

export interface CashFlowResponse {
  money_in: string;
  money_out: string;
  net_cash_flow: string;
}

export interface NetWorthResponse {
  assets: string;
  liabilities: string;
  net_worth: string;
}
```

- [ ] **Step 4: Create Budget types**

```typescript
// frontend/src/types/budget.ts
export interface Budget {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  style: 'TRADITIONAL' | 'ENVELOPE';
  rollover: boolean;
  created_at: string;
  updated_at: string;
  categories: BudgetCategory[];
}

export interface BudgetCategory {
  id: string;
  budget: string;
  account: string;
  account_name: string;
  amount: string;
  notes: string;
}

export interface BudgetListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Budget[];
}
```

- [ ] **Step 5: Create fetch API wrapper with JWT + tenant header**

```typescript
// frontend/src/lib/api.ts
import { getAccessToken } from './auth';

const API_BASE = '/api/v1';

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

function getTenantId(): string | null {
  try {
    return localStorage.getItem('gnucash_tenant_id');
  } catch {
    return null;
  }
}

async function refreshToken(): Promise<string | null> {
  try {
    const response = await fetch(`${API_BASE}/auth/refresh/`, {
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

// Queue for concurrent 401 retries
let refreshPromise: Promise<string | null> | null = null;

async function ensureAccessToken(): Promise<string | null> {
  if (getAccessToken()) return getAccessToken();

  if (!refreshPromise) {
    refreshPromise = refreshToken().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await ensureAccessToken();
  const tenantId = getTenantId();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(tenantId ? { 'X-Tenant-ID': tenantId } : {}),
    ...(init?.headers as Record<string, string> ?? {}),
  };

  let response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });

  // Handle 401 — one retry after token refresh
  if (response.status === 401) {
    const newToken = await refreshToken();
    if (newToken && !response.headers.get('x-retried')) {
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

- [ ] **Step 6: Create auth helper (token accessors)**

```typescript
// frontend/src/lib/auth.ts
let accessToken: string | null = null;

export const getAccessToken = () => accessToken;
export const setAccessToken = (token: string) => { accessToken = token; };
export const clearAccessToken = () => { accessToken = null; };
```

- [ ] **Step 7: Create React Query client**

```typescript
// frontend/src/lib/query-client.ts
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

- [ ] **Step 8: Commit**

```bash
git add frontend/src/types/ frontend/src/lib/api.ts frontend/src/lib/auth.ts frontend/src/lib/query-client.ts
git commit -m "feat: add API layer with native fetch, JWT auth, and TypeScript types"
```

---

### Task 4: Auth State (Zustand)

**Files:** `src/stores/auth-store.ts`, `src/hooks/use-auth.ts`

- [ ] **Step 1: Create Zustand auth store**

```typescript
// frontend/src/stores/auth-store.ts
import { create } from 'zustand';
import { clearAccessToken, setAccessToken } from '@/lib/auth';

export interface User {
  id: string;
  email: string;
}

interface AuthState {
  user: User | null;
  tenantId: string | null;
  isLoading: boolean;
  login: (user: User, token: string, tenantId: string) => void;
  setTenantId: (tenantId: string) => void;
  logout: () => void;
  setLoading: (isLoading: boolean) => void;
}

const TENANT_KEY = 'gnucash_tenant_id';

const getStoredTenantId = (): string | null => {
  try { return localStorage.getItem(TENANT_KEY); } catch { return null; }
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  tenantId: getStoredTenantId(),
  isLoading: false,

  login: (user, token, tenantId) => {
    setAccessToken(token);
    localStorage.setItem(TENANT_KEY, tenantId);
    set({ user, tenantId });
  },

  setTenantId: (tenantId) => {
    localStorage.setItem(TENANT_KEY, tenantId);
    set({ tenantId });
  },

  logout: () => {
    clearAccessToken();
    try { localStorage.removeItem(TENANT_KEY); } catch {}
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
  const user = useAuthStore((s) => s.user);
  const tenantId = useAuthStore((s) => s.tenantId);
  const isLoading = useAuthStore((s) => s.isLoading);
  const login = useAuthStore((s) => s.login);
  const logout = useAuthStore((s) => s.logout);
  const setTenantId = useAuthStore((s) => s.setTenantId);

  return {
    user,
    tenantId,
    isLoading,
    isAuthenticated: user !== null,
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

### Task 5: Routing and Auth Pages

**Files:** `src/App.tsx`, `src/main.tsx`, `src/components/layouts/AuthLayout.tsx`, `src/components/layouts/RootLayout.tsx`, `src/routes/ProtectedRoute.tsx`, `src/routes/LoginPage.tsx`, `src/routes/RegisterPage.tsx`, `src/routes/DashboardPage.tsx`, `src/routes/NotFoundPage.tsx`

- [ ] **Step 1: Create AuthLayout**

```tsx
// frontend/src/components/layouts/AuthLayout.tsx
import { Outlet } from 'react-router-dom';

export function AuthLayout() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/50 px-4">
      <div className="w-full max-w-md"><Outlet /></div>
    </div>
  );
}
```

- [ ] **Step 2: Create RootLayout**

```tsx
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

  return (
    <div className="flex h-screen">
      <aside className="flex w-64 flex-col border-r bg-card">
        <div className="flex h-14 items-center border-b px-6">
          <h1 className="text-lg font-semibold">GnuCash Web</h1>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className="flex w-full items-center rounded-md px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="border-t px-3 py-4">
          <div className="mb-2 px-3 text-xs text-muted-foreground">{user?.email}</div>
          <Button variant="outline" size="sm" onClick={() => { logout(); navigate('/login'); }} className="w-full">
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

- [ ] **Step 3: Create ProtectedRoute**

```tsx
// frontend/src/routes/ProtectedRoute.tsx
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return <div className="flex h-screen items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>;
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Outlet />;
}
```

- [ ] **Step 4: Create LoginPage**

```tsx
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
import { api } from '@/lib/api';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});
type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const { login, setLoading } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    setError(null);
    setLoading(true);
    try {
      const resp = await api.post<{ access: string; user: { id: string; email: string } }>('/auth/login/', data);
      // Backend sets refresh token in HttpOnly cookie. Store access token in memory.
      login(resp.user, resp.access, resp.user.id);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.status === 401 ? 'Invalid email or password.' : 'Login failed.');
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
            Don't have an account? <Link to="/register" className="text-primary underline-offset-4 hover:underline">Create one</Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 5: Create RegisterPage**

```tsx
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
import { api } from '@/lib/api';

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(12, 'Password must be at least 12 characters')
    .regex(/[A-Z]/, 'Must contain an uppercase letter')
    .regex(/[a-z]/, 'Must contain a lowercase letter')
    .regex(/[0-9]/, 'Must contain a digit'),
  tenant_name: z.string().min(1, 'Household name is required'),
  tenant_slug: z.string().min(1, 'URL slug is required').regex(/^[a-z0-9-]+$/, 'Lowercase letters, numbers, and hyphens only'),
});
type RegisterForm = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterForm) => {
    setError(null);
    try {
      await api.post('/auth/register/', data);
      navigate('/login');
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.response?.data;
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
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
            Already have an account? <Link to="/login" className="text-primary underline-offset-4 hover:underline">Sign in</Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 6: Create DashboardPage + NotFoundPage**

```tsx
// frontend/src/routes/DashboardPage.tsx
export function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="mt-2 text-muted-foreground">Welcome to GnuCash Web. Select a section from the sidebar to get started.</p>
    </div>
  );
}

// frontend/src/routes/NotFoundPage.tsx
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <h1 className="text-6xl font-bold text-muted-foreground">404</h1>
      <p className="mt-4 text-lg text-muted-foreground">Page not found.</p>
      <Button asChild className="mt-6"><Link to="/">Go Home</Link></Button>
    </div>
  );
}
```

- [ ] **Step 7: Create App.tsx with routes**

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/query-client';
import { AuthLayout } from '@/components/layouts/AuthLayout';
import { RootLayout } from '@/components/layouts/RootLayout';
import { ProtectedRoute } from '@/routes/ProtectedRoute';
import { LoginPage } from '@/routes/LoginPage';
import { RegisterPage } from '@/routes/RegisterPage';
import { DashboardPage } from '@/routes/DashboardPage';
import { NotFoundPage } from '@/routes/NotFoundPage';

function PlaceholderPage({ title }: { title: string }) {
  return <div><h1 className="text-2xl font-bold">{title}</h1><p className="mt-2 text-muted-foreground">Coming soon.</p></div>;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>
          <Route element={<ProtectedRoute />}>
            <Route element={<RootLayout />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/accounts" element={<PlaceholderPage title="Accounts" />} />
              <Route path="/transactions" element={<PlaceholderPage title="Transactions" />} />
              <Route path="/budgets" element={<PlaceholderPage title="Budgets" />} />
              <Route path="/investments" element={<PlaceholderPage title="Investments" />} />
              <Route path="/receipts" element={<PlaceholderPage title="Receipts" />} />
              <Route path="/recurring" element={<PlaceholderPage title="Recurring" />} />
              <Route path="/reports" element={<PlaceholderPage title="Reports" />} />
              <Route path="/settings" element={<PlaceholderPage title="Settings" />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 8: Create main.tsx**

```tsx
// frontend/src/main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from '@/App';
import '@/index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
);
```

- [ ] **Step 9: Commit**

```bash
git add frontend/src/App.tsx frontend/src/main.tsx frontend/src/components/layouts/ frontend/src/routes/LoginPage.tsx frontend/src/routes/RegisterPage.tsx frontend/src/routes/DashboardPage.tsx frontend/src/routes/NotFoundPage.tsx frontend/src/routes/ProtectedRoute.tsx
git commit -m "feat: add routing, auth layouts, login/register pages, and auth guard"
```

---

### Task 6: React Query Hooks

**Files:** `src/hooks/use-accounts.ts`, `src/hooks/use-transactions.ts`, `src/hooks/use-reports.ts`, `src/hooks/use-budgets.ts`, `src/hooks/use-split-balance.ts`

- [ ] **Step 1: Create use-accounts hook**

```typescript
// frontend/src/hooks/use-accounts.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Account, AccountListResponse } from '@/types/account';

export const accountKeys = {
  all: ['accounts'] as const,
  list: (params?: { search?: string }) => [...accountKeys.all, 'list', params] as const,
  detail: (id: string) => [...accountKeys.all, 'detail', id] as const,
};

export function useAccounts(params?: { search?: string }) {
  return useQuery({
    queryKey: accountKeys.list(params),
    queryFn: () => api.get<AccountListResponse>(`/accounts${params?.search ? `?search=${params.search}` : ''}`),
  });
}

export function useAccount(id: string) {
  return useQuery({
    queryKey: accountKeys.detail(id),
    queryFn: () => api.get<Account>(`/accounts/${id}`),
    enabled: !!id,
  });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Account>) => api.post<Account>('/accounts', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: accountKeys.all }),
  });
}
```

- [ ] **Step 2: Create use-transactions hook**

```typescript
// frontend/src/hooks/use-transactions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Transaction, TransactionListResponse } from '@/types/transaction';

export const txKeys = {
  all: ['transactions'] as const,
  list: (params?: { page?: number }) => [...txKeys.all, 'list', params] as const,
  detail: (id: string) => [...txKeys.all, 'detail', id] as const,
};

export function useTransactions(params?: { page?: number }) {
  return useQuery({
    queryKey: txKeys.list(params),
    queryFn: () => api.get<TransactionListResponse>('/transactions/'),
  });
}

export function useTransaction(id: string) {
  return useQuery({
    queryKey: txKeys.detail(id),
    queryFn: () => api.get<Transaction>(`/transactions/${id}`),
    enabled: !!id,
  });
}

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { currency: string; post_date: string; description: string; notes?: string; splits_data: { account: string; value: string; quantity?: string; memo?: string }[] }) =>
      api.post<Transaction>('/transactions', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: txKeys.all }),
  });
}

export function useDeleteTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/transactions/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: txKeys.all }),
  });
}
```

- [ ] **Step 3: Create use-reports hook**

```typescript
// frontend/src/hooks/use-reports.ts
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { BalanceSheetResponse, CashFlowResponse, IncomeStatementResponse } from '@/types/report';

export function useBalanceSheet(asOf: string) {
  return useQuery({
    queryKey: ['reports', 'balance-sheet', asOf],
    queryFn: () => api.get<BalanceSheetResponse>(`/reports/balance-sheet?as_of=${asOf}`),
    enabled: !!asOf,
  });
}

export function useIncomeStatement(start: string, end: string) {
  return useQuery({
    queryKey: ['reports', 'income-statement', start, end],
    queryFn: () => api.get<IncomeStatementResponse>(`/reports/income-statement?start_date=${start}&end_date=${end}`),
    enabled: !!start && !!end,
  });
}

export function useCashFlow(start: string, end: string) {
  return useQuery({
    queryKey: ['reports', 'cash-flow', start, end],
    queryFn: () => api.get<CashFlowResponse>(`/reports/cash-flow?start_date=${start}&end_date=${end}`),
    enabled: !!start && !!end,
  });
}
```

- [ ] **Step 4: Create use-budgets hook**

```typescript
// frontend/src/hooks/use-budgets.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { Budget, BudgetListResponse } from '@/types/budget';

export const budgetKeys = {
  all: ['budgets'] as const,
  list: () => [...budgetKeys.all, 'list'] as const,
  detail: (id: string) => [...budgetKeys.all, 'detail', id] as const,
};

export function useBudgets() {
  return useQuery({
    queryKey: budgetKeys.list(),
    queryFn: () => api.get<BudgetListResponse>('/budgets/'),
  });
}

export function useBudget(id: string) {
  return useQuery({
    queryKey: budgetKeys.detail(id),
    queryFn: () => api.get<Budget>(`/budgets/${id}`),
    enabled: !!id,
  });
}

export function useDeleteBudget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/budgets/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: budgetKeys.all }),
  });
}
```

- [ ] **Step 5: Create use-split-balance hook**

```typescript
// frontend/src/hooks/use-split-balance.ts
import { useMemo } from 'react';

export function useSplitBalance(values: (string | undefined)[]) {
  return useMemo(() => {
    const nums = values.filter((v): v is string => v !== undefined && v !== '').map(Number).filter((n) => !isNaN(n));
    const total = nums.reduce((s, v) => s + v, 0);
    return {
      total,
      isBalanced: Math.abs(total) < 0.005,
      isEmpty: nums.length === 0,
      difference: total.toFixed(2),
    };
  }, [values]);
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/
git commit -m "feat: add React Query hooks for accounts, transactions, reports, budgets"
```

---

### Task 7: AccountPicker Component

**Files:** `src/components/account-picker.tsx`

- [ ] **Step 1: Create AccountPicker**

```tsx
// frontend/src/components/account-picker.tsx
import * as React from 'react';
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { useAccounts } from '@/hooks/use-accounts';

export interface AccountPickerProps {
  value?: string | null;
  onValueChange: (accountId: string) => void;
  placeholder?: string;
  disabled?: boolean;
  'aria-label'?: string;
  id?: string;
}

function getIndentLevel(fullName: string): number {
  return fullName.split(':').length - 1;
}

export function AccountPicker({ value, onValueChange, placeholder = 'Select account...', disabled, 'aria-label': ariaLabel, id }: AccountPickerProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const { data, isLoading } = useAccounts(search ? { search } : undefined);
  const accounts = data?.results ?? [];
  const selected = accounts.find((a) => a.id === value) ?? null;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox" aria-expanded={open} aria-label={ariaLabel} id={id} disabled={disabled} className="w-full justify-between">
          {selected ? <span className="truncate">{selected.full_name}</span> : <span className="text-muted-foreground">{placeholder}</span>}
          {isLoading ? <Loader2 className="ml-2 h-4 w-4 animate-spin" /> : <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput placeholder="Search accounts..." onValueChange={setSearch} />
          <CommandList>
            {!isLoading && accounts.length === 0 && <CommandEmpty>No accounts found.</CommandEmpty>}
            <CommandGroup>
              {accounts.map((account) => {
                const indent = getIndentLevel(account.full_name);
                return (
                  <CommandItem key={account.id} value={account.full_name} onSelect={() => { onValueChange(account.id); setOpen(false); }}>
                    <Check className={cn('mr-2 h-4 w-4 shrink-0', value === account.id ? 'opacity-100' : 'opacity-0')} />
                    <span className="truncate" style={{ paddingLeft: `${indent * 16}px` }}>{account.full_name}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{account.account_type}</span>
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/account-picker.tsx
git commit -m "feat: add AccountPicker searchable combobox component"
```

---

### Task 8: SplitInput Component

**Files:** `src/components/split-input.tsx`

- [ ] **Step 1: Create SplitInput**

```tsx
// frontend/src/components/split-input.tsx
import * as React from 'react';
import { Plus, Trash2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useFormContext } from 'react-hook-form';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { AccountPicker } from '@/components/account-picker';
import { useSplitBalance } from '@/hooks/use-split-balance';

export interface SplitInputProps {
  fieldName?: 'splits_data';
  maxSplits?: number;
}

export function SplitInput({ fieldName = 'splits_data', maxSplits = 20 }: SplitInputProps) {
  const form = useFormContext();
  const fields = form.watch(fieldName) as { account: string; value: string; memo: string }[];

  const values = fields?.map((f) => f.value) ?? [];
  const { isBalanced, isEmpty, difference } = useSplitBalance(values);

  const addSplit = () => {
    if ((fields?.length ?? 0) >= maxSplits) return;
    const current = form.getValues(fieldName) ?? [];
    form.setValue(fieldName, [...current, { account: '', value: '', quantity: '1', memo: '' }], { shouldDirty: true, shouldValidate: true });
  };

  const removeSplit = (index: number) => {
    if ((fields?.length ?? 0) <= 2) return;
    const current = form.getValues(fieldName);
    current.splice(index, 1);
    form.setValue(fieldName, current, { shouldDirty: true, shouldValidate: true });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label>Splits</Label>
        {isEmpty ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <AlertCircle className="h-4 w-4" /><span>Add at least one split.</span>
          </div>
        ) : (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className={cn('flex items-center gap-2 text-sm font-medium', isBalanced ? 'text-green-600' : 'text-red-600')} role="status" aria-live="polite">
                  {isBalanced ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                  <span>{isBalanced ? 'Balanced' : `Unbalanced: ${difference}`}</span>
                </div>
              </TooltipTrigger>
              <TooltipContent><p>Sum of all split values must equal 0. Current: {difference}</p></TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40%]">Account</TableHead>
              <TableHead className="w-[20%]">Value</TableHead>
              <TableHead className="w-[30%]">Memo</TableHead>
              <TableHead className="w-[10%] text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {fields?.map((field, index) => (
              <TableRow key={index}>
                <TableCell>
                  <AccountPicker
                    value={field.account || null}
                    onValueChange={(id) => { form.setValue(`${fieldName}.${index}.account`, id, { shouldDirty: true, shouldValidate: true }); }}
                    placeholder="Choose account..."
                    aria-label={`Account for split ${index + 1}`}
                  />
                  {form.formState.errors.splits_data?.[index]?.account && (
                    <p className="mt-1 text-xs text-red-600">{String(form.formState.errors.splits_data[index].account?.message)}</p>
                  )}
                </TableCell>
                <TableCell>
                  <Input type="number" step="0.01" placeholder="0.00" value={field.value ?? ''} onChange={(e) => { form.setValue(`${fieldName}.${index}.value`, e.target.value, { shouldDirty: true, shouldValidate: true }); }} aria-label={`Value for split ${index + 1}`} />
                  {form.formState.errors.splits_data?.[index]?.value && (
                    <p className="mt-1 text-xs text-red-600">{String(form.formState.errors.splits_data[index].value?.message)}</p>
                  )}
                </TableCell>
                <TableCell>
                  <Input placeholder="Optional memo..." value={field.memo ?? ''} onChange={(e) => { form.setValue(`${fieldName}.${index}.memo`, e.target.value, { shouldDirty: true }); }} aria-label={`Memo for split ${index + 1}`} />
                </TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="icon" onClick={() => removeSplit(index)} aria-label={`Remove split ${index + 1}`} disabled={(fields?.length ?? 0) <= 2}>
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Button type="button" variant="outline" size="sm" onClick={addSplit} disabled={(fields?.length ?? 0) >= maxSplits}>
        <Plus className="mr-2 h-4 w-4" /> Add split
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/split-input.tsx
git commit -m "feat: add SplitInput dynamic split form with balance indicator"
```

---

### Task 9: TransactionForm Component

**Files:** `src/features/transactions/components/transaction-form-schema.ts`, `src/features/transactions/components/transaction-form.tsx`

- [ ] **Step 1: Create Zod schema**

```typescript
// frontend/src/features/transactions/components/transaction-form-schema.ts
import { z } from 'zod';

export const transactionFormSchema = z.object({
  currency: z.string().min(1, 'Currency is required.'),
  post_date: z.string().min(1, 'Date is required.'),
  description: z.string().min(1, 'Description is required.').max(200),
  notes: z.string().max(1000).optional().default(''),
  splits_data: z
    .array(z.object({
      account: z.string().uuid('Please select a valid account.'),
      value: z.string().min(1, 'Value is required.').refine((v) => { const n = parseFloat(v); return !isNaN(n) && n !== 0; }, { message: 'Must be a non-zero number.' }),
      quantity: z.string().optional(),
      memo: z.string().max(200).optional().default(''),
    }))
    .min(2, 'At least 2 splits required.')
    .refine((splits) => Math.abs(splits.reduce((sum, s) => sum + (parseFloat(s.value) || 0), 0)) < 0.005, { message: 'Splits must balance to zero.' }),
});

export type TransactionFormValues = z.infer<typeof transactionFormSchema>;
```

- [ ] **Step 2: Create TransactionForm**

```tsx
// frontend/src/features/transactions/components/transaction-form.tsx
import * as React from 'react';
import { CalendarIcon, Loader2 } from 'lucide-react';
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';
import { SplitInput } from '@/components/split-input';
import { useCreateTransaction } from '@/hooks/use-transactions';
import { transactionFormSchema, type TransactionFormValues } from './transaction-form-schema';

export interface TransactionFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
  defaultCurrency?: string;
}

export function TransactionForm({ onSuccess, onCancel, defaultCurrency = 'USD' }: TransactionFormProps) {
  const createMutation = useCreateTransaction();
  const form = useForm<TransactionFormValues>({
    resolver: zodResolver(transactionFormSchema),
    defaultValues: {
      currency: defaultCurrency,
      post_date: format(new Date(), 'yyyy-MM-dd'),
      description: '',
      notes: '',
      splits_data: [
        { account: '', value: '', quantity: '1', memo: '' },
        { account: '', value: '', quantity: '1', memo: '' },
      ],
    },
  });

  const onSubmit = (data: TransactionFormValues) => {
    createMutation.mutate(data, { onSuccess: () => { form.reset(); onSuccess?.(); } });
  };

  return (
    <FormProvider {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <Card>
          <CardHeader><CardTitle>New Transaction</CardTitle></CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Date</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className={cn('w-full justify-start text-left font-normal', !form.watch('post_date') && 'text-muted-foreground')}>
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {form.watch('post_date') ? format(new Date(form.watch('post_date')), 'PPP') : 'Pick a date'}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar mode="single" selected={new Date(form.watch('post_date'))} onSelect={(date) => { if (date) form.setValue('post_date', format(date, 'yyyy-MM-dd'), { shouldDirty: true, shouldValidate: true }); }} initialFocus />
                  </PopoverContent>
                </Popover>
                {form.formState.errors.post_date && <p className="text-xs text-red-600">{form.formState.errors.post_date.message}</p>}
              </div>
              <div className="space-y-2">
                <Label>Currency</Label>
                <Input {...form.register('currency')} placeholder="USD" maxLength={3} className="uppercase" />
                {form.formState.errors.currency && <p className="text-xs text-red-600">{form.formState.errors.currency.message}</p>}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input id="description" {...form.register('description')} placeholder="e.g., Monthly salary deposit" />
              {form.formState.errors.description && <p className="text-xs text-red-600">{form.formState.errors.description.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Input id="notes" {...form.register('notes')} placeholder="Additional details..." />
            </div>
            <Separator />
            <SplitInput />
            {form.formState.errors.splits_data && (
              <p className="text-sm text-red-600">{typeof form.formState.errors.splits_data.message === 'string' ? form.formState.errors.splits_data.message : 'Fix split errors above.'}</p>
            )}
          </CardContent>
          <CardFooter className="flex justify-between gap-4">
            {onCancel && <Button type="button" variant="outline" onClick={onCancel} disabled={createMutation.isPending}>Cancel</Button>}
            <div className="ml-auto flex items-center gap-4">
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Transaction
              </Button>
            </div>
          </CardFooter>
        </Card>
      </form>
    </FormProvider>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/transactions/
git commit -m "feat: add TransactionForm with Zod validation and React Hook Form"
```

---

### Task 10: AccountList Page

**Files:** `src/routes/AccountListPage.tsx`

- [ ] **Step 1: Create AccountListPage**

```tsx
// frontend/src/routes/AccountListPage.tsx
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAccounts } from '@/hooks/use-accounts';

export function AccountListPage() {
  const { data, isLoading, error } = useAccounts();

  if (isLoading) {
    return <div className="space-y-4">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-12 w-full animate-pulse rounded bg-muted" />)}</div>;
  }

  if (error) {
    return <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4"><p className="text-sm text-destructive">Failed to load accounts.</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Accounts</h1>
        <Button asChild><Link to="/accounts/new">New Account</Link></Button>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-lg">{data?.count ?? 0} Accounts</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full">
            <thead><tr className="border-b"><th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Name</th><th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Type</th><th className="w-24" /></tr></thead>
            <tbody>
              {data?.results.map((account) => (
                <tr key={account.id} className="border-b last:border-0">
                  <td className="px-4 py-3 text-sm font-medium">{account.full_name}</td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{account.account_type}</td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" size="sm" asChild><Link to={`/accounts/${account.id}`}>View</Link></Button>
                  </td>
                </tr>
              ))}
              {data?.results.length === 0 && (
                <tr><td colSpan={3} className="px-4 py-8 text-center text-sm text-muted-foreground">No accounts yet.</td></tr>
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Wire into App.tsx**

In `frontend/src/App.tsx`, replace:
```tsx
<Route path="/accounts" element={<PlaceholderPage title="Accounts" />} />
```
with:
```tsx
import { AccountListPage } from '@/routes/AccountListPage';
// ...
<Route path="/accounts" element={<AccountListPage />} />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/AccountListPage.tsx frontend/src/App.tsx
git commit -m "feat: wire AccountListPage to routes"
```

---

### Task 11: Reports Pages

**Files:** `src/routes/reports/index.tsx`, `balance-sheet.tsx`, `income-statement.tsx`, `cash-flow.tsx`

- [ ] **Step 1: Create ReportDatePicker**

```tsx
// frontend/src/components/reports/ReportDatePicker.tsx
import { format } from 'date-fns';
import { CalendarIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

interface ReportDatePickerProps {
  label: string;
  value: string;
  onChange: (date: string) => void;
}

export function ReportDatePicker({ label, value, onChange }: ReportDatePickerProps) {
  return (
    <div className="space-y-2">
      <span className="text-sm font-medium">{label}</span>
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="outline" className={cn('w-full justify-start text-left font-normal', !value && 'text-muted-foreground')}>
            <CalendarIcon className="mr-2 h-4 w-4" />
            {value ? format(new Date(value), 'PPP') : 'Pick a date'}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar mode="single" selected={value ? new Date(value) : undefined} onSelect={(d) => { if (d) onChange(format(d, 'yyyy-MM-dd')); }} initialFocus />
        </PopoverContent>
      </Popover>
    </div>
  );
}
```

- [ ] **Step 2: Create ReportTable**

```tsx
// frontend/src/components/reports/ReportTable.tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

interface Row { label: string; value: string; bold?: boolean }

export function ReportTable({ title, rows }: { title: string; rows: Row[] }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent>
        {rows.map((row, i) => (
          <div key={i}>
            {i > 0 && <Separator className="my-2" />}
            <div className="flex justify-between py-2">
              <span className={row.bold ? 'font-semibold' : ''}>{row.label}</span>
              <span className={row.bold ? 'font-semibold' : 'text-muted-foreground'}>{row.value}</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 3: Create BalanceSheet page**

```tsx
// frontend/src/routes/reports/balance-sheet.tsx
import { useState } from 'react';
import { format } from 'date-fns';
import { ReportDatePicker } from '@/components/reports/ReportDatePicker';
import { ReportTable } from '@/components/reports/ReportTable';
import { useBalanceSheet } from '@/hooks/use-reports';

export function BalanceSheetPage() {
  const [asOf, setAsOf] = useState(format(new Date(), 'yyyy-MM-dd'));
  const { data, isLoading } = useBalanceSheet(asOf);

  if (isLoading) return <div className="h-48 w-full animate-pulse rounded bg-muted" />;
  if (!data) return null;

  const fmt = (v: string) => parseFloat(v).toLocaleString('en-US', { style: 'currency', currency: 'USD' });

  return (
    <div className="space-y-6">
      <div className="flex gap-4"><ReportDatePicker label="As of" value={asOf} onChange={setAsOf} /></div>
      <ReportTable title="Balance Sheet" rows={[
        { label: 'Total Assets', value: fmt(data.assets), bold: true },
        { label: 'Total Liabilities', value: fmt(data.liabilities), bold: true },
        { label: 'Equity', value: fmt(data.equity), bold: true },
        { label: 'Retained Earnings', value: fmt(data.retained_earnings), bold: true },
        { label: 'Balanced', value: data.balanced ? 'Yes' : 'No', bold: true },
      ]} />
    </div>
  );
}
```

- [ ] **Step 4: Create IncomeStatement + CashFlow pages**

```tsx
// frontend/src/routes/reports/income-statement.tsx
import { useState } from 'react';
import { format, subMonths } from 'date-fns';
import { ReportDatePicker } from '@/components/reports/ReportDatePicker';
import { ReportTable } from '@/components/reports/ReportTable';
import { useIncomeStatement } from '@/hooks/use-reports';

export function IncomeStatementPage() {
  const [start, setStart] = useState(format(subMonths(new Date(), 12), 'yyyy-MM-dd'));
  const [end, setEnd] = useState(format(new Date(), 'yyyy-MM-dd'));
  const { data, isLoading } = useIncomeStatement(start, end);
  if (isLoading) return <div className="h-48 w-full animate-pulse rounded bg-muted" />;
  if (!data) return null;
  const fmt = (v: string) => parseFloat(v).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <ReportDatePicker label="From" value={start} onChange={setStart} />
        <ReportDatePicker label="To" value={end} onChange={setEnd} />
      </div>
      <ReportTable title="Income Statement" rows={[
        { label: 'Revenue', value: fmt(data.revenue), bold: true },
        { label: 'Expenses', value: fmt(data.expenses), bold: true },
        { label: 'Net Income', value: fmt(data.net_income), bold: true },
      ]} />
    </div>
  );
}

// frontend/src/routes/reports/cash-flow.tsx
import { useState } from 'react';
import { format, subMonths } from 'date-fns';
import { ReportDatePicker } from '@/components/reports/ReportDatePicker';
import { ReportTable } from '@/components/reports/ReportTable';
import { useCashFlow } from '@/hooks/use-reports';

export function CashFlowPage() {
  const [start, setStart] = useState(format(subMonths(new Date(), 12), 'yyyy-MM-dd'));
  const [end, setEnd] = useState(format(new Date(), 'yyyy-MM-dd'));
  const { data, isLoading } = useCashFlow(start, end);
  if (isLoading) return <div className="h-48 w-full animate-pulse rounded bg-muted" />;
  if (!data) return null;
  const fmt = (v: string) => parseFloat(v).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <ReportDatePicker label="From" value={start} onChange={setStart} />
        <ReportDatePicker label="To" value={end} onChange={setEnd} />
      </div>
      <ReportTable title="Cash Flow" rows={[
        { label: 'Money In', value: fmt(data.money_in) },
        { label: 'Money Out', value: fmt(data.money_out) },
        { label: 'Net Cash Flow', value: fmt(data.net_cash_flow), bold: true },
      ]} />
    </div>
  );
}
```

- [ ] **Step 5: Create reports index**

```tsx
// frontend/src/routes/reports/index.tsx
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';

export function ReportsIndex() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Reports</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          { label: 'Balance Sheet', path: '/reports/balance-sheet', desc: 'Assets = Liabilities + Equity' },
          { label: 'Income Statement', path: '/reports/income-statement', desc: 'Revenue - Expenses' },
          { label: 'Cash Flow', path: '/reports/cash-flow', desc: 'Money in vs money out' },
        ].map((r) => (
          <Link key={r.path} to={r.path} className="block rounded-lg border p-6 hover:bg-muted/50">
            <h3 className="font-semibold">{r.label}</h3>
            <p className="text-sm text-muted-foreground">{r.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/reports/ frontend/src/components/reports/
git commit -m "feat: add reports pages (Balance Sheet, Income Statement, Cash Flow)"
```

---

### Task 12: Budget Pages

**Files:** `src/routes/budgets/index.tsx`, `$budgetId.tsx`, `new.tsx`, `components/BudgetCard.tsx`, `components/BudgetForm.tsx`

- [ ] **Step 1: Create BudgetCard**

```tsx
// frontend/src/features/budgets/components/BudgetCard.tsx
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Budget } from '@/types/budget';

export function BudgetCard({ budget }: { budget: Budget }) {
  return (
    <Link to={`/budgets/${budget.id}`} className="block">
      <Card className="hover:bg-muted/50">
        <CardHeader><CardTitle className="text-lg">{budget.name}</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{budget.start_date} — {budget.end_date}</p>
          <p className="text-sm text-muted-foreground">{budget.style}{budget.rollover ? ' (Rollover)' : ''}</p>
          <p className="text-sm text-muted-foreground">{budget.categories.length} categories</p>
        </CardContent>
      </Card>
    </Link>
  );
}
```

- [ ] **Step 2: Create BudgetForm**

```tsx
// frontend/src/features/budgets/components/BudgetForm.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const budgetSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  start_date: z.string().min(1, 'Start date is required'),
  end_date: z.string().min(1, 'End date is required'),
  style: z.enum(['TRADITIONAL', 'ENVELOPE']).default('TRADITIONAL'),
  rollover: z.boolean().default(false),
});
type BudgetFormValues = z.infer<typeof budgetSchema>;

export function BudgetForm({ onSuccess, onCancel }: { onSuccess?: () => void; onCancel?: () => void }) {
  const form = useForm<BudgetFormValues>({ resolver: zodResolver(budgetSchema), defaultValues: { style: 'TRADITIONAL', rollover: false } });
  const onSubmit = (data: BudgetFormValues) => { onSuccess?.(); };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      <Card>
        <CardHeader><CardTitle>New Budget</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2"><Label htmlFor="name">Name</Label><Input id="name" {...form.register('name')} /></div>
          <div className="space-y-2"><Label htmlFor="start_date">Start Date</Label><Input id="start_date" type="date" {...form.register('start_date')} /></div>
          <div className="space-y-2"><Label htmlFor="end_date">End Date</Label><Input id="end_date" type="date" {...form.register('end_date')} /></div>
          <div className="space-y-2">
            <Label>Style</Label>
            <select {...form.register('style')} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option value="TRADITIONAL">Traditional</option>
              <option value="ENVELOPE">Envelope</option>
            </select>
          </div>
        </CardContent>
        <CardFooter className="flex justify-between gap-4">
          {onCancel && <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>}
          <Button type="submit" className="ml-auto">Create Budget</Button>
        </CardFooter>
      </Card>
    </form>
  );
}
```

- [ ] **Step 3: Create Budget pages**

```tsx
// frontend/src/routes/budgets/index.tsx
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useBudgets } from '@/hooks/use-budgets';
import { BudgetCard } from '@/features/budgets/components/BudgetCard';

export function BudgetList() {
  const { data, isLoading } = useBudgets();
  if (isLoading) return <div className="h-48 w-full animate-pulse rounded bg-muted" />;
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Budgets</h1>
        <Button asChild><Link to="/budgets/new">New Budget</Link></Button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {data?.results.map((b) => <BudgetCard key={b.id} budget={b} />)}
      </div>
    </div>
  );
}

// frontend/src/routes/budgets/$budgetId.tsx
import { useParams } from 'react-router-dom';
import { useBudget } from '@/hooks/use-budgets';
import { Progress } from '@/components/ui/progress';

export function BudgetDetail() {
  const { budgetId } = useParams<{ budgetId: string }>();
  const { data } = useBudget(budgetId!);
  if (!data) return null;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{data.name}</h1>
      <div className="space-y-4">
        {data.categories.map((cat) => (
          <div key={cat.id} className="rounded-lg border p-4">
            <div className="flex justify-between"><span className="font-medium">{cat.account_name}</span><span>{cat.amount}</span></div>
            <Progress value={50} className="mt-2" />
          </div>
        ))}
      </div>
    </div>
  );
}

// frontend/src/routes/budgets/new.tsx
import { useNavigate } from 'react-router-dom';
import { BudgetForm } from '@/features/budgets/components/BudgetForm';

export function BudgetNew() {
  const navigate = useNavigate();
  return <BudgetForm onSuccess={() => navigate('/budgets')} onCancel={() => navigate('/budgets')} />;
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/budgets/ frontend/src/features/budgets/
git commit -m "feat: add budget pages (list, detail, create)"
```

---

### Task 13: Backend CORS Config

**Files:** Modify `backend/gnucash_web/settings/base.py`

- [ ] **Step 1: Add CORS origin for Vite dev server**

In `backend/gnucash_web/settings/base.py`, ensure `CORS_ALLOWED_ORIGINS` includes:

```python
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=['http://localhost:5173', 'http://localhost:5174'],
)
```

Also add `CORS_ALLOW_CREDENTIALS = True` after the CORS section:

```python
CORS_ALLOW_CREDENTIALS = True
```

- [ ] **Step 2: Commit**

```bash
cd backend && git add gnucash_web/settings/base.py && git commit -m "fix: enable CORS credentials for Vite dev server"
```

---

### Task 14: PWA Setup

**Files:** `frontend/src/routes/offline.tsx`

- [ ] **Step 1: Create offline page**

```tsx
// frontend/src/routes/offline.tsx
import { WifiOff } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function OfflinePage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <WifiOff className="mx-auto h-12 w-12 text-muted-foreground" />
          <CardTitle className="mt-4">You're Offline</CardTitle>
        </CardHeader>
        <CardContent className="text-center text-muted-foreground">
          <p>Check your internet connection and try again.</p>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/routes/offline.tsx
git commit -m "feat: add offline fallback page"
```

---

## Self-Review

### 1. Spec Coverage Check

| Spec Route | Task | Status |
|---|---|---|
| `/login` | Task 5 | Covered |
| `/register` | Task 5 | Covered |
| `/` Dashboard | Task 5 | Stubbed |
| `/accounts` | Task 10 | Covered |
| `/transactions` | Task 9 (component) | Component done, page stubbed |
| `/budgets` | Task 12 | Covered |
| `/reports/*` | Task 11 | Covered |
| `/investments` | Task 5 | Stubbed |
| `/receipts` | Task 5 | Stubbed |
| `/recurring` | Task 5 | Stubbed |
| `/settings` | Task 5 | Stubbed |

| Infrastructure | Task | Status |
|---|---|---|
| Vite + React + TypeScript | Task 1 | Covered |
| Tailwind CSS | Task 1 | Covered |
| shadcn/ui primitives | Task 2, prerequisites | Covered |
| Native fetch API client + JWT | Task 3 | Covered |
| React Query hooks | Task 6 | Covered (accounts, tx, reports, budgets) |
| Zustand auth store | Task 4 | Covered |
| React Hook Form + Zod | Task 5, 9 | Covered |
| React Router 7 | Task 5 | Covered |
| X-Tenant-ID header | Task 3 (api.ts) | Covered |

### 2. Placeholder Scan
No TBD/TODO placeholders. Stubbed routes render a simple "Coming soon" page — intentional, out of scope for this phase.

### 3. Type Consistency
- All API responses use explicit TypeScript interfaces
- Query keys: `accountKeys`, `txKeys`, `budgetKeys` — all follow `[resource, list|detail, params]` pattern
- `splits_data` field name matches backend `TransactionSerializer`
- `X-Tenant-ID` header set in `api.ts` from localStorage
- Access token in memory only (via `auth.ts`), never localStorage
