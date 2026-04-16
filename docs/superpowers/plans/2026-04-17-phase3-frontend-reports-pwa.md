# Phase 3: Frontend Reports, Budgets & PWA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the tenant-facing frontend React app with report pages (Balance Sheet, Income Statement, Cash Flow), budget management (list + detail with budgeted-vs-actual), and PWA support (service worker, offline page, manifest). The backend report and budget endpoints already exist from Phase 1.

**Architecture:** Vite + React + TypeScript + React Router v6 + shadcn/ui. Server state via React Query, client state via Zustand, forms via React Hook Form + Zod. PWA via `vite-plugin-pwa`.

**Tech Stack:** Vite 6, React 19, TypeScript 5, React Query (TanStack), shadcn/ui (Radix + Tailwind), React Router v6, React Hook Form, Zod, `vite-plugin-pwa`

---

## File Map

### Files to Create (frontend app scaffolding)
- `frontend/package.json` — Dependencies and scripts
- `frontend/tsconfig.json` — TypeScript config (strict mode)
- `frontend/tsconfig.node.json` — Node TypeScript config for Vite
- `frontend/vite.config.ts` — Vite config with PWA plugin
- `frontend/tailwind.config.ts` — Tailwind CSS config
- `frontend/postcss.config.js` — PostCSS config
- `frontend/index.html` — HTML entry point
- `frontend/src/main.tsx` — App entry point
- `frontend/src/App.tsx` — Root component with routes
- `frontend/src/lib/api.ts` — Axios API client with tenant header injection
- `frontend/src/lib/queryClient.ts` — React Query client setup
- `frontend/src/types/reports.ts` — TypeScript types for report responses
- `frontend/src/types/budgets.ts` — TypeScript types for budget responses
- `frontend/src/hooks/useTenant.ts` — Hook to get current tenant from auth context

### Files to Create (report pages)
- `frontend/src/routes/reports.tsx` — Reports index/selector page
- `frontend/src/routes/reports/balance-sheet.tsx` — Balance Sheet page
- `frontend/src/routes/reports/income-statement.tsx` — Income Statement page
- `frontend/src/routes/reports/cash-flow.tsx` — Cash Flow page
- `frontend/src/components/reports/ReportDatePicker.tsx` — Date range picker shared across report pages
- `frontend/src/components/reports/ReportTable.tsx` — Generic tabular report display

### Files to Create (budget pages)
- `frontend/src/routes/budgets.tsx` — Budget list page
- `frontend/src/routes/budgets/$budgetId.tsx` — Budget detail page
- `frontend/src/routes/budgets/new.tsx` — Create budget form
- `frontend/src/routes/budgets/$budgetId/edit.tsx` — Edit budget form
- `frontend/src/features/budgets/components/BudgetList.tsx` — Budget list component
- `frontend/src/features/budgets/components/BudgetCard.tsx` — Budget card component
- `frontend/src/features/budgets/components/BudgetDetail.tsx` — Budget detail with progress bars
- `frontend/src/features/budgets/components/BudgetForm.tsx` — Create/edit budget form
- `frontend/src/features/budgets/hooks/useBudgets.ts` — React Query hooks for budgets

### Files to Create (PWA)
- `frontend/public/icons/icon-192.png` — App icon 192x192
- `frontend/public/icons/icon-512.png` — App icon 512x512
- `frontend/src/routes/offline.tsx` — Offline fallback page

### Files to Modify (backend — wiring)
- `backend/gnucash_web/settings/base.py` — Add CORS allowed origins for Vite dev server

---

### Task 1: Frontend App Scaffolding

**Files:** All scaffolding files listed above

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
    "preview": "vite preview"
  },
  "dependencies": {
    "@hookform/resolvers": "^4.1.0",
    "@radix-ui/react-dropdown-menu": "^2.1.5",
    "@radix-ui/react-label": "^2.1.2",
    "@radix-ui/react-progress": "^1.1.2",
    "@radix-ui/react-select": "^2.1.6",
    "@radix-ui/react-slot": "^1.1.2",
    "@radix-ui/react-tabs": "^1.1.3",
    "@tanstack/react-query": "^5.66.0",
    "axios": "^1.7.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "date-fns": "^4.1.0",
    "lucide-react": "^0.475.0",
    "react": "^19.0.0",
    "react-day-picker": "^9.5.0",
    "react-dom": "^19.0.0",
    "react-hook-form": "^7.54.0",
    "react-router-dom": "^7.1.0",
    "tailwind-merge": "^3.0.0",
    "zod": "^3.24.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@types/node": "^22.10.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.5.0",
    "tailwindcss": "^3.4.17",
    "typescript": "~5.7.0",
    "vite": "^6.0.0",
    "vite-plugin-pwa": "^0.21.0"
  }
}
```

- [ ] **Step 2: Create TypeScript configs**

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
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
    "noUncheckedSideEffectImports": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
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
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 3: Create Vite config with PWA plugin**

```typescript
// frontend/vite.config.ts
import react from '@vitejs/plugin-react'
import path from 'path'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icons/icon-192.png', 'icons/icon-512.png'],
      manifest: {
        name: 'GnuCash Web',
        short_name: 'GnuCash',
        description: 'Personal finance and accounting for the web',
        theme_color: '#0f172a',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
        icons: [
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'gstatic-fonts-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365,
              },
            },
          },
        ],
      },
    }),
  ],
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
})
```

- [ ] **Step 4: Create Tailwind and PostCSS configs**

```typescript
// frontend/tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [],
} satisfies Config
```

```js
// frontend/postcss.config.js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 5: Create index.html**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#0f172a" />
    <meta name="description" content="GnuCash Web — Personal finance and accounting" />
    <link rel="manifest" href="/manifest.webmanifest" />
    <link rel="icon" href="/icons/icon-192.png" />
    <title>GnuCash Web</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Create API client, query client, and type definitions**

```typescript
// frontend/src/lib/api.ts
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  const tenantId = localStorage.getItem('current_tenant_id')
  if (tenantId) {
    config.headers['X-Tenant-ID'] = tenantId
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const { data } = await axios.post('/api/v1/auth/refresh/', {
          refresh: localStorage.getItem('refresh_token'),
        })
        localStorage.setItem('access_token', data.access)
        originalRequest.headers.Authorization = `Bearer ${data.access}`
        return api(originalRequest)
      } catch {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default api
```

```typescript
// frontend/src/lib/queryClient.ts
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})
```

```typescript
// frontend/src/types/reports.ts
export interface BalanceSheetReport {
  assets: string
  liabilities: string
  equity: string
  retained_earnings: string
  balanced: boolean
}

export interface IncomeStatementReport {
  revenue: string
  expenses: string
  net_income: string
}

export interface CashFlowReport {
  operating_activities: string
  investing_activities: string
  financing_activities: string
  net_cash_flow: string
}
```

```typescript
// frontend/src/types/budgets.ts
export interface BudgetCategory {
  id: string
  account_id: string
  account_name: string
  amount: string
  actual: string
}

export interface Budget {
  id: string
  name: string
  start_date: string
  end_date: string
  style: 'TRADITIONAL' | 'ENVELOPE'
  rollover: boolean
  categories: BudgetCategory[]
}

export interface BudgetListItem {
  id: string
  name: string
  start_date: string
  end_date: string
  style: 'TRADITIONAL' | 'ENVELOPE'
  total_budgeted: string
  total_actual: string
}

export interface BudgetFormData {
  name: string
  start_date: string
  end_date: string
  style: 'TRADITIONAL' | 'ENVELOPE'
  rollover: boolean
  categories: {
    account_id: string
    amount: string
  }[]
}
```

- [ ] **Step 7: Create tenant hook**

```typescript
// frontend/src/hooks/useTenant.ts
export function useTenant(): string {
  const tenantId = localStorage.getItem('current_tenant_id')
  if (!tenantId) {
    throw new Error('No tenant selected. User must be authenticated and have a tenant.')
  }
  return tenantId
}
```

- [ ] **Step 8: Create main.tsx entry point**

```typescript
// frontend/src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { queryClient } from './lib/queryClient'
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
```

- [ ] **Step 9: Create global CSS**

```css
/* frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold frontend app with Vite, React, TypeScript, Tailwind, PWA"
```

---

### Task 2: Reports Pages

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/routes/reports.tsx`
- Create: `frontend/src/routes/reports/balance-sheet.tsx`
- Create: `frontend/src/routes/reports/income-statement.tsx`
- Create: `frontend/src/routes/reports/cash-flow.tsx`
- Create: `frontend/src/components/reports/ReportDatePicker.tsx`
- Create: `frontend/src/components/reports/ReportTable.tsx`

- [ ] **Step 1: Create App.tsx with routing**

```typescript
// frontend/src/App.tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import ReportsPage from './routes/reports'
import BalanceSheetPage from './routes/reports/balance-sheet'
import IncomeStatementPage from './routes/reports/income-statement'
import CashFlowPage from './routes/reports/cash-flow'

export default function App() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <nav className="container mx-auto flex h-14 items-center gap-6">
          <a href="/" className="font-semibold">GnuCash Web</a>
          <a href="/reports" className="text-sm text-muted-foreground hover:text-foreground">
            Reports
          </a>
          <a href="/budgets" className="text-sm text-muted-foreground hover:text-foreground">
            Budgets
          </a>
        </nav>
      </header>
      <main className="container mx-auto py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/reports" replace />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/reports/balance-sheet" element={<BalanceSheetPage />} />
          <Route path="/reports/income-statement" element={<IncomeStatementPage />} />
          <Route path="/reports/cash-flow" element={<CashFlowPage />} />
        </Routes>
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Create shared ReportDatePicker component**

```typescript
// frontend/src/components/reports/ReportDatePicker.tsx
import { format } from 'date-fns'
import { CalendarIcon } from 'lucide-react'
import { useState } from 'react'

interface ReportDatePickerProps {
  label: string
  date: Date | undefined
  onDateChange: (date: Date | undefined) => void
}

export function ReportDatePicker({ label, date, onDateChange }: ReportDatePickerProps) {
  const [inputValue, setInputValue] = useState(date ? format(date, 'yyyy-MM-dd') : '')

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value
    setInputValue(value)
    if (value) {
      const parsed = new Date(value + 'T00:00:00')
      if (!isNaN(parsed.getTime())) {
        onDateChange(parsed)
      }
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-medium text-muted-foreground">{label}</label>
      <div className="flex items-center gap-2">
        <CalendarIcon className="h-4 w-4 text-muted-foreground" />
        <input
          type="date"
          value={inputValue}
          onChange={handleChange}
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create shared ReportTable component**

```typescript
// frontend/src/components/reports/ReportTable.tsx
interface ReportRow {
  label: string
  value: string
  bold?: boolean
  indent?: boolean
}

interface ReportTableProps {
  title: string
  rows: ReportRow[]
  asOfDate?: string
}

function formatCurrency(value: string): string {
  const num = parseFloat(value)
  if (isNaN(num)) return value
  const formatted = Math.abs(num).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  return num < 0 ? `(${formatted})` : formatted
}

export function ReportTable({ title, rows, asOfDate }: ReportTableProps) {
  return (
    <div className="rounded-lg border bg-card">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">{title}</h2>
        {asOfDate && (
          <p className="text-sm text-muted-foreground">As of {asOfDate}</p>
        )}
      </div>
      <div className="px-6 py-4">
        <table className="w-full">
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className={row.bold ? 'border-t font-semibold' : ''}>
                <td className={`py-2 text-sm ${row.indent ? 'pl-6' : ''}`}>
                  {row.label}
                </td>
                <td className={`py-2 text-right text-sm tabular-nums ${row.bold ? 'font-semibold' : ''}`}>
                  {formatCurrency(row.value)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create Reports index page**

```typescript
// frontend/src/routes/reports.tsx
import { Link } from 'react-router-dom'

const reportLinks = [
  {
    href: '/reports/balance-sheet',
    title: 'Balance Sheet',
    description: 'Assets, liabilities, and equity at a point in time',
  },
  {
    href: '/reports/income-statement',
    title: 'Income Statement',
    description: 'Revenue, expenses, and net income over a period',
  },
  {
    href: '/reports/cash-flow',
    title: 'Cash Flow',
    description: 'Cash movements from operating, investing, and financing',
  },
]

export default function ReportsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Reports</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {reportLinks.map((link) => (
          <Link
            key={link.href}
            to={link.href}
            className="block rounded-lg border bg-card p-6 hover:bg-accent transition-colors"
          >
            <h3 className="font-semibold">{link.title}</h3>
            <p className="text-sm text-muted-foreground mt-1">{link.description}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Create Balance Sheet page**

```typescript
// frontend/src/routes/reports/balance-sheet.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import api from '../../lib/api'
import { ReportDatePicker } from '../../components/reports/ReportDatePicker'
import { ReportTable } from '../../components/reports/ReportTable'
import type { BalanceSheetReport } from '../../types/reports'

export default function BalanceSheetPage() {
  const [asOf, setAsOf] = useState<Date>(new Date())

  const { data, isLoading, error } = useQuery<BalanceSheetReport>({
    queryKey: ['reports', 'balance-sheet', asOf?.toISOString()],
    queryFn: async () => {
      const { data } = await api.get<BalanceSheetReport>('/reports/balance-sheet', {
        params: { as_of: format(asOf, 'yyyy-MM-dd') },
      })
      return data
    },
    enabled: !!asOf,
  })

  if (isLoading) return <p className="text-muted-foreground">Loading...</p>
  if (error) return <p className="text-destructive">Failed to load report: {String(error)}</p>
  if (!data) return null

  const rows = [
    { label: 'Assets', value: data.assets, bold: true },
    { label: 'Liabilities', value: data.liabilities, bold: true },
    { label: 'Equity', value: data.equity, bold: true },
    { label: 'Retained Earnings', value: data.retained_earnings },
    { label: 'Balanced', value: data.balanced ? 'Yes' : 'No', bold: true },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Balance Sheet</h1>
      <div className="flex gap-6 mb-6">
        <ReportDatePicker
          label="As of Date"
          date={asOf}
          onDateChange={setAsOf}
        />
      </div>
      <ReportTable
        title="Balance Sheet"
        rows={rows}
        asOfDate={format(asOf, 'MMMM d, yyyy')}
      />
    </div>
  )
}
```

- [ ] **Step 6: Create Income Statement page**

```typescript
// frontend/src/routes/reports/income-statement.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import api from '../../lib/api'
import { ReportDatePicker } from '../../components/reports/ReportDatePicker'
import { ReportTable } from '../../components/reports/ReportTable'
import type { IncomeStatementReport } from '../../types/reports'

export default function IncomeStatementPage() {
  const today = new Date()
  const [startDate, setStartDate] = useState<Date>(
    new Date(today.getFullYear(), 0, 1),
  )
  const [endDate, setEndDate] = useState<Date>(today)

  const { data, isLoading, error } = useQuery<IncomeStatementReport>({
    queryKey: ['reports', 'income-statement', startDate?.toISOString(), endDate?.toISOString()],
    queryFn: async () => {
      const { data } = await api.get<IncomeStatementReport>('/reports/income-statement', {
        params: {
          start_date: format(startDate, 'yyyy-MM-dd'),
          end_date: format(endDate, 'yyyy-MM-dd'),
        },
      })
      return data
    },
    enabled: !!startDate && !!endDate,
  })

  if (isLoading) return <p className="text-muted-foreground">Loading...</p>
  if (error) return <p className="text-destructive">Failed to load report: {String(error)}</p>
  if (!data) return null

  const rows = [
    { label: 'Revenue', value: data.revenue, bold: true },
    { label: 'Expenses', value: data.expenses, bold: true },
    { label: 'Net Income', value: data.net_income, bold: true },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Income Statement</h1>
      <div className="flex gap-6 mb-6">
        <ReportDatePicker
          label="Start Date"
          date={startDate}
          onDateChange={setStartDate}
        />
        <ReportDatePicker
          label="End Date"
          date={endDate}
          onDateChange={setEndDate}
        />
      </div>
      <ReportTable
        title="Income Statement"
        rows={rows}
        asOfDate={`${format(startDate, 'MMM d, yyyy')} — ${format(endDate, 'MMM d, yyyy')}`}
      />
    </div>
  )
}
```

- [ ] **Step 7: Create Cash Flow page**

```typescript
// frontend/src/routes/reports/cash-flow.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import api from '../../lib/api'
import { ReportDatePicker } from '../../components/reports/ReportDatePicker'
import { ReportTable } from '../../components/reports/ReportTable'
import type { CashFlowReport } from '../../types/reports'

export default function CashFlowPage() {
  const today = new Date()
  const [startDate, setStartDate] = useState<Date>(
    new Date(today.getFullYear(), 0, 1),
  )
  const [endDate, setEndDate] = useState<Date>(today)

  const { data, isLoading, error } = useQuery<CashFlowReport>({
    queryKey: ['reports', 'cash-flow', startDate?.toISOString(), endDate?.toISOString()],
    queryFn: async () => {
      const { data } = await api.get<CashFlowReport>('/reports/cash-flow', {
        params: {
          start_date: format(startDate, 'yyyy-MM-dd'),
          end_date: format(endDate, 'yyyy-MM-dd'),
        },
      })
      return data
    },
    enabled: !!startDate && !!endDate,
  })

  if (isLoading) return <p className="text-muted-foreground">Loading...</p>
  if (error) return <p className="text-destructive">Failed to load report: {String(error)}</p>
  if (!data) return null

  const rows = [
    { label: 'Operating Activities', value: data.operating_activities, bold: true },
    { label: 'Investing Activities', value: data.investing_activities, bold: true },
    { label: 'Financing Activities', value: data.financing_activities, bold: true },
    { label: 'Net Cash Flow', value: data.net_cash_flow, bold: true },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Cash Flow</h1>
      <div className="flex gap-6 mb-6">
        <ReportDatePicker
          label="Start Date"
          date={startDate}
          onDateChange={setStartDate}
        />
        <ReportDatePicker
          label="End Date"
          date={endDate}
          onDateChange={setEndDate}
        />
      </div>
      <ReportTable
        title="Cash Flow Statement"
        rows={rows}
        asOfDate={`${format(startDate, 'MMM d, yyyy')} — ${format(endDate, 'MMM d, yyyy')}`}
      />
    </div>
  )
}
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/routes/reports/ frontend/src/components/reports/ frontend/src/App.tsx
git commit -m "feat: add report pages (balance sheet, income statement, cash flow) with date pickers"
```

---

### Task 3: Budget Pages

**Files:**
- Create: `frontend/src/routes/budgets.tsx`
- Create: `frontend/src/routes/budgets/$budgetId.tsx`
- Create: `frontend/src/routes/budgets/new.tsx`
- Create: `frontend/src/routes/budgets/$budgetId/edit.tsx`
- Create: `frontend/src/features/budgets/components/BudgetList.tsx`
- Create: `frontend/src/features/budgets/components/BudgetCard.tsx`
- Create: `frontend/src/features/budgets/components/BudgetDetail.tsx`
- Create: `frontend/src/features/budgets/components/BudgetForm.tsx`
- Create: `frontend/src/features/budgets/hooks/useBudgets.ts`

- [ ] **Step 1: Create budget React Query hooks**

```typescript
// frontend/src/features/budgets/hooks/useBudgets.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../../lib/api'
import type { Budget, BudgetListItem, BudgetFormData } from '../../../types/budgets'

export function useBudgets() {
  return useQuery<BudgetListItem[]>({
    queryKey: ['budgets'],
    queryFn: async () => {
      const { data } = await api.get<BudgetListItem[]>('/budgets')
      return data
    },
  })
}

export function useBudget(id: string) {
  return useQuery<Budget>({
    queryKey: ['budget', id],
    queryFn: async () => {
      const { data } = await api.get<Budget>(`/budgets/${id}`)
      return data
    },
    enabled: !!id,
  })
}

export function useCreateBudget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (formData: BudgetFormData) => {
      const { data } = await api.post<Budget>('/budgets', formData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
    },
  })
}

export function useUpdateBudget(id: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (formData: BudgetFormData) => {
      const { data } = await api.put<Budget>(`/budgets/${id}`, formData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] })
      queryClient.invalidateQueries({ queryKey: ['budget', id] })
    },
  })
}
```

- [ ] **Step 2: Create BudgetCard component**

```typescript
// frontend/src/features/budgets/components/BudgetCard.tsx
import { Link } from 'react-router-dom'
import { Progress } from '../../../components/ui/progress'
import type { BudgetListItem } from '../../../types/budgets'

interface BudgetCardProps {
  budget: BudgetListItem
}

function calculatePercentage(budgeted: string, actual: string): number {
  const b = parseFloat(budgeted)
  const a = parseFloat(actual)
  if (isNaN(b) || b === 0) return 0
  const pct = (Math.abs(a) / b) * 100
  return Math.min(pct, 100)
}

export function BudgetCard({ budget }: BudgetCardProps) {
  const pct = calculatePercentage(budget.total_budgeted, budget.total_actual)

  return (
    <Link
      to={`/budgets/${budget.id}`}
      className="block rounded-lg border bg-card p-6 hover:bg-accent transition-colors"
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold">{budget.name}</h3>
        <span className="text-xs text-muted-foreground">
          {budget.style}
        </span>
      </div>
      <div className="mb-2">
        <Progress value={pct} className="h-2" />
      </div>
      <div className="flex justify-between text-sm text-muted-foreground">
        <span>Budgeted: {budget.total_budgeted}</span>
        <span>Actual: {budget.total_actual}</span>
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        {budget.start_date} to {budget.end_date}
      </p>
    </Link>
  )
}
```

- [ ] **Step 3: Create BudgetList component**

```typescript
// frontend/src/features/budgets/components/BudgetList.tsx
import { Link } from 'react-router-dom'
import { useBudgets } from '../hooks/useBudgets'
import { BudgetCard } from './BudgetCard'

export function BudgetList() {
  const { data, isLoading, error } = useBudgets()

  if (isLoading) return <p className="text-muted-foreground">Loading budgets...</p>
  if (error) return <p className="text-destructive">Failed to load budgets</p>
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground mb-4">No budgets yet.</p>
        <Link
          to="/budgets/new"
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Create Budget
        </Link>
      </div>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {data.map((budget) => (
        <BudgetCard key={budget.id} budget={budget} />
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Create BudgetDetail component**

```typescript
// frontend/src/features/budgets/components/BudgetDetail.tsx
import { Progress } from '../../../components/ui/progress'
import type { Budget } from '../../../types/budgets'

interface BudgetDetailProps {
  budget: Budget
}

function calculateProgress(budgeted: string, actual: string): number {
  const b = parseFloat(budgeted)
  const a = parseFloat(actual)
  if (isNaN(b) || b === 0) return 0
  const pct = (Math.abs(a) / b) * 100
  return Math.min(pct, 100)
}

function progressColor(pct: number): string {
  if (pct >= 100) return 'bg-destructive'
  if (pct >= 75) return 'bg-orange-500'
  return 'bg-primary'
}

export function BudgetDetail({ budget }: BudgetDetailProps) {
  const totalBudgeted = budget.categories.reduce(
    (sum, c) => sum + parseFloat(c.amount), 0,
  )
  const totalActual = budget.categories.reduce(
    (sum, c) => sum + parseFloat(c.actual), 0,
  )

  return (
    <div className="rounded-lg border bg-card">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">{budget.name}</h2>
        <p className="text-sm text-muted-foreground">
          {budget.start_date} to {budget.end_date} &middot; {budget.style}
        </p>
      </div>
      <div className="px-6 py-4">
        {/* Summary row */}
        <div className="mb-6 grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-sm text-muted-foreground">Total Budgeted</p>
            <p className="text-lg font-semibold">{totalBudgeted.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Total Actual</p>
            <p className="text-lg font-semibold">{totalActual.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Remaining</p>
            <p className="text-lg font-semibold">{(totalBudgeted - totalActual).toFixed(2)}</p>
          </div>
        </div>

        {/* Category rows */}
        <div className="space-y-4">
          {budget.categories.map((cat) => {
            const pct = calculateProgress(cat.amount, cat.actual)
            const remaining = parseFloat(cat.amount) - parseFloat(cat.actual)
            return (
              <div key={cat.id} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium">{cat.account_name}</span>
                  <span className="text-muted-foreground">
                    {cat.actual} / {cat.amount}
                  </span>
                </div>
                <div className="relative">
                  <Progress
                    value={pct}
                    className="h-2"
                  />
                  <span
                    className={`absolute right-0 -top-5 text-xs font-medium ${pct >= 100 ? 'text-destructive' : 'text-muted-foreground'}`}
                  >
                    {pct.toFixed(0)}%
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {remaining >= 0 ? `${remaining.toFixed(2)} remaining` : `${Math.abs(remaining).toFixed(2)} over budget`}
                </p>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Create BudgetForm component**

```typescript
// frontend/src/features/budgets/components/BudgetForm.tsx
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import type { BudgetFormData } from '../../../types/budgets'

const budgetSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  start_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Invalid date'),
  end_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Invalid date'),
  style: z.enum(['TRADITIONAL', 'ENVELOPE']),
  rollover: z.boolean(),
  categories: z.array(
    z.object({
      account_id: z.string().min(1, 'Account is required'),
      amount: z.string().regex(/^\d+(\.\d{1,2})?$/, 'Invalid amount'),
    }),
  ).min(1, 'At least one category is required'),
})

type BudgetFormValues = z.infer<typeof budgetSchema>

interface BudgetFormProps {
  defaultValues?: Partial<BudgetFormData>
  onSubmit: (data: BudgetFormValues) => void
  isSubmitting?: boolean
}

export function BudgetForm({ defaultValues, onSubmit, isSubmitting }: BudgetFormProps) {
  const { register, control, handleSubmit, formState: { errors } } = useForm<BudgetFormValues>({
    resolver: zodResolver(budgetSchema),
    defaultValues: {
      name: defaultValues?.name ?? '',
      start_date: defaultValues?.start_date ?? '',
      end_date: defaultValues?.end_date ?? '',
      style: defaultValues?.style ?? 'TRADITIONAL',
      rollover: defaultValues?.rollover ?? false,
      categories: defaultValues?.categories ?? [{ account_id: '', amount: '' }],
    },
  })

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'categories',
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Name</label>
          <input
            {...register('name')}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
          {errors.name && <p className="text-xs text-destructive mt-1">{errors.name.message}</p>}
        </div>
        <div>
          <label className="text-sm font-medium">Style</label>
          <select
            {...register('style')}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          >
            <option value="TRADITIONAL">Traditional</option>
            <option value="ENVELOPE">Envelope</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Start Date</label>
          <input
            type="date"
            {...register('start_date')}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
          {errors.start_date && <p className="text-xs text-destructive mt-1">{errors.start_date.message}</p>}
        </div>
        <div>
          <label className="text-sm font-medium">End Date</label>
          <input
            type="date"
            {...register('end_date')}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          />
          {errors.end_date && <p className="text-xs text-destructive mt-1">{errors.end_date.message}</p>}
        </div>
      </div>

      {/* Categories */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium">Categories</h3>
          <button
            type="button"
            onClick={() => append({ account_id: '', amount: '' })}
            className="text-xs text-primary hover:underline"
          >
            + Add Category
          </button>
        </div>
        <div className="space-y-2">
          {fields.map((field, i) => (
            <div key={field.id} className="flex gap-2 items-end">
              <div className="flex-1">
                <label className="text-xs text-muted-foreground">Account</label>
                <input
                  {...register(`categories.${i}.account_id`)}
                  placeholder="Account ID"
                  className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                />
              </div>
              <div className="w-40">
                <label className="text-xs text-muted-foreground">Amount</label>
                <input
                  {...register(`categories.${i}.amount`)}
                  placeholder="0.00"
                  className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
                />
              </div>
              <button
                type="button"
                onClick={() => remove(i)}
                className="text-xs text-destructive hover:underline pb-2"
              >
                Remove
              </button>
            </div>
          ))}
          {errors.categories?.root && (
            <p className="text-xs text-destructive">{errors.categories.root.message}</p>
          )}
        </div>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      >
        {isSubmitting ? 'Saving...' : 'Save Budget'}
      </button>
    </form>
  )
}
```

- [ ] **Step 6: Create budget route pages**

```typescript
// frontend/src/routes/budgets.tsx
import { Link } from 'react-router-dom'
import { BudgetList } from '../features/budgets/components/BudgetList'

export default function BudgetsPage() {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Budgets</h1>
        <Link
          to="/budgets/new"
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          New Budget
        </Link>
      </div>
      <BudgetList />
    </div>
  )
}
```

```typescript
// frontend/src/routes/budgets/$budgetId.tsx
import { useParams, Link } from 'react-router-dom'
import { useBudget } from '../../features/budgets/hooks/useBudgets'
import { BudgetDetail } from '../../features/budgets/components/BudgetDetail'

export default function BudgetDetailPage() {
  const { budgetId } = useParams<{ budgetId: string }>()

  const { data, isLoading, error } = useBudget(budgetId ?? '')

  if (isLoading) return <p className="text-muted-foreground">Loading budget...</p>
  if (error) return <p className="text-destructive">Failed to load budget</p>
  if (!data) return <p className="text-muted-foreground">Budget not found</p>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{data.name}</h1>
        <Link
          to={`/budgets/${data.id}/edit`}
          className="text-sm text-primary hover:underline"
        >
          Edit
        </Link>
      </div>
      <BudgetDetail budget={data} />
    </div>
  )
}
```

```typescript
// frontend/src/routes/budgets/new.tsx
import { useNavigate } from 'react-router-dom'
import { useCreateBudget } from '../../features/budgets/hooks/useBudgets'
import { BudgetForm } from '../../features/budgets/components/BudgetForm'

export default function NewBudgetPage() {
  const navigate = useNavigate()
  const createBudget = useCreateBudget()

  function handleSubmit(data: Parameters<typeof createBudget.mutate>[0]) {
    createBudget.mutate(data, {
      onSuccess: (budget) => {
        navigate(`/budgets/${budget.id}`)
      },
    })
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">New Budget</h1>
      <BudgetForm onSubmit={handleSubmit} isSubmitting={createBudget.isPending} />
    </div>
  )
}
```

```typescript
// frontend/src/routes/budgets/$budgetId/edit.tsx
import { useParams, useNavigate } from 'react-router-dom'
import { useBudget, useUpdateBudget } from '../../../features/budgets/hooks/useBudgets'
import { BudgetForm } from '../../../features/budgets/components/BudgetForm'

export default function EditBudgetPage() {
  const { budgetId } = useParams<{ budgetId: string }>()
  const navigate = useNavigate()
  const { data } = useBudget(budgetId ?? '')
  const updateBudget = useUpdateBudget(budgetId ?? '')

  function handleSubmit(formData: Parameters<typeof updateBudget.mutate>[0]) {
    updateBudget.mutate(formData, {
      onSuccess: () => {
        navigate(`/budgets/${budgetId}`)
      },
    })
  }

  if (!data) return <p className="text-muted-foreground">Loading...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Edit Budget: {data.name}</h1>
      <BudgetForm
        defaultValues={{
          name: data.name,
          start_date: data.start_date,
          end_date: data.end_date,
          style: data.style,
          rollover: data.rollover,
          categories: data.categories.map((c) => ({
            account_id: c.account_id,
            amount: c.amount,
          })),
        }}
        onSubmit={handleSubmit}
        isSubmitting={updateBudget.isPending}
      />
    </div>
  )
}
```

- [ ] **Step 7: Wire budget routes into App.tsx**

Add to `frontend/src/App.tsx`:

```typescript
import BudgetsPage from './routes/budgets'
import BudgetDetailPage from './routes/budgets/$budgetId'
import NewBudgetPage from './routes/budgets/new'
import EditBudgetPage from './routes/budgets/$budgetId/edit'

// Inside <Routes>:
<Route path="/budgets" element={<BudgetsPage />} />
<Route path="/budgets/:budgetId" element={<BudgetDetailPage />} />
<Route path="/budgets/new" element={<NewBudgetPage />} />
<Route path="/budgets/:budgetId/edit" element={<EditBudgetPage />} />
```

- [ ] **Step 8: Create shadcn/ui Progress component**

```typescript
// frontend/src/components/ui/progress.tsx
import * as React from 'react'
import * as ProgressPrimitive from '@radix-ui/react-progress'
import { cn } from '../../lib/utils'

const Progress = React.forwardRef<
  React.ComponentRef<typeof ProgressPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root>
>(({ className, value, ...props }, ref) => (
  <ProgressPrimitive.Root
    ref={ref}
    className={cn('relative h-4 w-full overflow-hidden rounded-full bg-secondary', className)}
    {...props}
  >
    <ProgressPrimitive.Indicator
      className="h-full w-full flex-1 bg-primary transition-all"
      style={{ transform: `translateX(-${100 - (value ?? 0)}%)` }}
    />
  </ProgressPrimitive.Root>
))
Progress.displayName = ProgressPrimitive.Root.displayName

export { Progress }
```

```typescript
// frontend/src/lib/utils.ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 9: Commit**

```bash
git add frontend/src/routes/budgets/ frontend/src/features/budgets/ frontend/src/components/ui/progress.tsx frontend/src/lib/utils.ts frontend/src/App.tsx
git commit -m "feat: add budget list, detail, and CRUD pages with progress bars"
```

---

### Task 4: PWA — Offline Support

**Files:**
- Create: `frontend/src/routes/offline.tsx`
- Create: `frontend/public/icons/icon-192.png`
- Create: `frontend/public/icons/icon-512.png`

- [ ] **Step 1: Create offline fallback page**

```typescript
// frontend/src/routes/offline.tsx
import { useEffect, useState } from 'react'

export default function OfflinePage() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  useEffect(() => {
    function handleOnline() { setIsOnline(true) }
    function handleOffline() { setIsOnline(false) }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  if (isOnline) {
    return null
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="rounded-lg border bg-card p-8 max-w-md">
        <h1 className="text-xl font-bold mb-2">You are offline</h1>
        <p className="text-sm text-muted-foreground mb-4">
          Check your internet connection and try again. Cached data may still be available.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Retry
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Wire offline page into App.tsx**

Add a route for offline in `frontend/src/App.tsx`:

```typescript
import OfflinePage from './routes/offline'

// Inside <Routes>, at the end:
<Route path="/offline" element={<OfflinePage />} />
```

- [ ] **Step 3: Add network status detection to main layout**

Add to `frontend/src/App.tsx` the offline detection. Place an `OfflinePage` component at the bottom of the layout:

```typescript
import { useState, useEffect } from 'react'

// Inside the App component, before return:
const [isOnline, setIsOnline] = useState(navigator.onLine)
useEffect(() => {
  const on = () => setIsOnline(true)
  const off = () => setIsOnline(false)
  window.addEventListener('online', on)
  window.addEventListener('offline', off)
  return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off) }
}, [])

// At the bottom of the returned JSX, after </main>:
{!isOnline && (
  <div className="fixed bottom-4 left-4 z-50 rounded-lg bg-destructive px-4 py-2 text-sm text-destructive-foreground shadow-lg">
    You are offline. Some features may be unavailable.
  </div>
)}
```

- [ ] **Step 4: Generate placeholder icons**

The icons at `frontend/public/icons/icon-192.png` and `frontend/public/icons/icon-512.png` should be generated. For the initial implementation, create simple placeholder PNG files:

```bash
# Install sharp (image processing) as a dev dependency to generate icons:
cd frontend && npx --yes @vite-pwa/assets-generator --config pwa-assets.config.ts
```

Or manually create 192x192 and 512x512 PNG icons with the GnuCash branding and place them at:
- `frontend/public/icons/icon-192.png`
- `frontend/public/icons/icon-512.png`

For immediate testing, any valid PNG of the correct dimensions will work. The manifest references these exact paths.

- [ ] **Step 5: Verify PWA build**

```bash
cd frontend && npm run build
```

Expected output in `frontend/dist/`:
- `index.html` — with manifest link and PWA meta tags
- `manifest.webmanifest` — auto-generated by vite-plugin-pwa
- `sw.js` — service worker (auto-generated)
- `workbox-*.js` — workbox runtime
- Asset files (JS, CSS, icons)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/offline.tsx frontend/src/App.tsx frontend/public/icons/
git commit -m "feat: add PWA offline support with service worker and offline banner"
```

---

### Task 5: Backend CORS for Vite Dev Server

**Files:**
- Modify: `backend/gnucash_web/settings/base.py`

- [ ] **Step 1: Add CORS configuration**

Add to `backend/gnucash_web/settings/base.py`:

```python
# CORS (for local development with Vite dev server)
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=['http://localhost:5173', 'http://localhost:5174'],
)
CORS_ALLOW_CREDENTIALS = True
```

Ensure `'corsheaders',` is in `INSTALLED_APPS` and `'corsheaders.middleware.CorsMiddleware',` is in `MIDDLEWARE` (before `CommonMiddleware`).

- [ ] **Step 2: Commit**

```bash
git add backend/gnucash_web/settings/base.py
git commit -m "chore: add CORS config for Vite dev server"
```

---

## Self-Review

### 1. Spec Coverage Check

| Requirement | Task | Status |
|---|---|---|
| Balance Sheet page with date picker | Task 2 (Step 5) | Covered |
| Income Statement page with date range | Task 2 (Step 6) | Covered |
| Cash Flow page with date range | Task 2 (Step 7) | Covered |
| Read-only report display (tabular) | Task 2 (ReportTable component) | Covered |
| Budget list page | Task 3 (Step 6, BudgetList) | Covered |
| Budget detail with budgeted vs actual | Task 3 (BudgetDetail component) | Covered |
| Progress bars per category | Task 3 (Progress + BudgetDetail) | Covered |
| Create budget form | Task 3 (BudgetForm + new.tsx) | Covered |
| Edit budget form | Task 3 (BudgetForm + edit.tsx) | Covered |
| Vite PWA plugin setup | Task 1 (vite.config.ts) | Covered |
| Service worker for app shell | Task 1 (workbox config) | Covered |
| Offline page | Task 4 (offline.tsx) | Covered |
| Manifest.json with name, icons | Task 1 (manifest config) | Covered |
| Offline banner in layout | Task 4 (Step 3) | Covered |
| TypeScript strict, no `any` | All steps | Covered |
| CORS for dev server | Task 5 | Covered |

### 2. Placeholder Scan

- Account picker in BudgetForm uses a text input for `account_id` — a full account picker component (with search/dropdown) would replace this, but the text input is functional for the initial build. The `account_id` field is typed as `string` and validated by Zod.
- Icon generation (Step 4) requires either manual creation or running the assets-generator CLI — the PWA config itself is complete and will work with any valid PNGs at the expected paths.
- No other placeholders found.

### 3. Type/Name Consistency

- All React Query hooks follow the `['<resource>', <id>]` key pattern per the frontend-state rules.
- All mutations invalidate both list and detail query keys on success.
- Report types use `string` for monetary values (matching backend Decimal serialization to JSON).
- Budget form uses Zod schema with `zodResolver` — no manual validation in the component.
- All components use `React.forwardRef` only where needed (shadcn wrapper); UI components are plain functions.
- No `any` types used anywhere — all imports are typed.
- API paths match spec: `/api/v1/reports/balance-sheet`, `/api/v1/budgets/:id`.
