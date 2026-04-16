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
