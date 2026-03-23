import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  theme: 'dark' | 'light';
  language: string;
  notificationsEnabled: boolean;
  setTheme: (theme: 'dark' | 'light') => void;
  setLanguage: (lang: string) => void;
  setNotifications: (enabled: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'dark',
      language: 'en-US',
      notificationsEnabled: true,
      setTheme: (theme) => set({ theme }),
      setLanguage: (language) => set({ language }),
      setNotifications: (notificationsEnabled) => set({ notificationsEnabled }),
    }),
    {
      name: 'app-settings',
    }
  )
);
