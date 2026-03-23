"use client";

import { useAuthStore } from '@/store/authStore';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import api from '@/lib/api';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { setAuth } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await api.get('/api/auth/me');
        setAuth(res.data);
      } catch {
        if (pathname !== '/login') {
          router.push('/login');
        }
      } finally {
        setChecking(false);
      }
    };
    checkAuth();
  }, [pathname]);

  if (checking) return null;
  return <>{children}</>;
}
