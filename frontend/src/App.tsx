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
import { AccountListPage } from '@/routes/AccountListPage';
import { AccountRegisterPage } from '@/routes/AccountRegisterPage';
import { ReportsIndex } from '@/routes/reports';
import { BalanceSheetPage } from '@/routes/reports/balance-sheet';
import { IncomeStatementPage } from '@/routes/reports/income-statement';
import { CashFlowPage } from '@/routes/reports/cash-flow';

import { TransactionListPage } from '@/routes/TransactionListPage';
import { TransactionNewPage } from '@/routes/TransactionNewPage';
import { TransactionDetailPage } from '@/routes/TransactionDetailPage';

import { ReceiptListPage } from '@/routes/ReceiptListPage';
import { ReceiptUploadPage } from '@/routes/ReceiptUploadPage';
import { ReceiptDetailPage } from '@/routes/ReceiptDetailPage';
import { RecurringListPage } from '@/routes/RecurringListPage';
import { RecurringNewPage } from '@/routes/RecurringNewPage';

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
              <Route path="/accounts" element={<AccountListPage />} />
              <Route path="/accounts/:id" element={<AccountRegisterPage />} />
              <Route path="/transactions" element={<TransactionListPage />} />
              <Route path="/transactions/new" element={<TransactionNewPage />} />
              <Route path="/transactions/:id" element={<TransactionDetailPage />} />
              <Route path="/budgets" element={<PlaceholderPage title="Budgets" />} />
              <Route path="/investments" element={<PlaceholderPage title="Investments" />} />
              <Route path="/receipts" element={<ReceiptListPage />} />
              <Route path="/receipts/upload" element={<ReceiptUploadPage />} />
              <Route path="/receipts/:id" element={<ReceiptDetailPage />} />
              <Route path="/recurring" element={<RecurringListPage />} />
              <Route path="/recurring/new" element={<RecurringNewPage />} />
              <Route path="/reports" element={<ReportsIndex />} />
              <Route path="/reports/balance-sheet" element={<BalanceSheetPage />} />
              <Route path="/reports/income-statement" element={<IncomeStatementPage />} />
              <Route path="/reports/cash-flow" element={<CashFlowPage />} />
              <Route path="/settings" element={<PlaceholderPage title="Settings" />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
