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
