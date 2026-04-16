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
