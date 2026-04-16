// admin/src/stores/auth-store.ts
import { create } from 'zustand';

interface AuthUser {
  id: string;
  email: string;
  is_staff: boolean;
  is_superuser: boolean;
}

interface AuthState {
  user: AuthUser | null;
  isLoading: boolean;
  login: (user: AuthUser, accessToken: string) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  login: (user, accessToken) => {
    localStorage.setItem('gnucash_access_token', accessToken);
    set({ user, isLoading: false });
  },
  logout: () => {
    localStorage.removeItem('gnucash_access_token');
    set({ user: null });
  },
  setLoading: (loading) => set({ isLoading: loading }),
}));
