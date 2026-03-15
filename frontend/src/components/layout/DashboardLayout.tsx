"use client";

import React from 'react';
import Sidebar from './Sidebar';
import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { token, user } = useAuthStore();
  const router = useRouter();

  React.useEffect(() => {
    if (!token) {
      router.push('/login');
    }
  }, [token, router]);

  if (!token) return null;

  return (
    <div className="flex bg-[#0a0a0b] min-h-screen text-white">
      <Sidebar />
      <main className="flex-1 ml-64 p-8">
        <header className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-sm font-medium text-slate-500 uppercase tracking-widest">N-Tier Intelligence</h1>
            <p className="text-2xl font-semibold mt-1">Strategic Operations</p>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="text-sm font-medium">{user?.username || 'User'}</p>
              <p className="text-xs text-slate-500 capitalize">{user?.role || 'Analyst'}</p>
            </div>
            <div className="w-10 h-10 rounded-full bg-blue-600/20 border border-blue-500/20 flex items-center justify-center text-blue-500 font-bold">
              {user?.username?.charAt(0).toUpperCase()}
            </div>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
