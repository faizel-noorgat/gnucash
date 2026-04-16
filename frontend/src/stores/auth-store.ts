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
