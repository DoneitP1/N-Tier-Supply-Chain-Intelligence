import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '@/lib/api';

interface AuthState {
  user: {
    username: string;
    role: string;
  } | null;
  _hasHydrated: boolean;
  setAuth: (user: { username: string; role: string }) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      _hasHydrated: false,
      setAuth: (user) => {
        set({ user });
      },
      logout: async () => {
        try {
          await api.post('/api/auth/logout');
        } catch (err) {
          console.error("Logout request failed", err);
        }
        set({ user: null });
      },
    }),
    {
      name: 'auth-storage',
      onRehydrateStorage: () => () => {
        useAuthStore.setState({ _hasHydrated: true });
      },
    }
  )
);
