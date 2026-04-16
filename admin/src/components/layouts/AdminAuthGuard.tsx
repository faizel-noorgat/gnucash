// admin/src/routes/AdminAuthGuard.tsx
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
