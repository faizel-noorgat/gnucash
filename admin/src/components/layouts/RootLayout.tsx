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
