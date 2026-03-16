"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Database, 
  Activity, 
  Settings, 
  LogOut,
  Files,
  Network
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/lib/utils';

export default function Sidebar() {
  const pathname = usePathname();
  const logout = useAuthStore((state) => state.logout);

  const navItems = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Knowledge Graph', href: '/graph', icon: Network },
    { name: 'Ingestion', href: '/ingestion', icon: Files },
    { name: 'Risk Analytics', href: '/risk', icon: Activity },
    { name: 'Data Management', href: '/data', icon: Database },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-[#111113] border-r border-[#1e293b] flex flex-col h-screen fixed left-0 top-0">
      <div className="p-6">
        <h2 className="text-2xl font-bold gradient-text">N-Tier AI</h2>
      </div>

      <nav className="flex-1 px-4 space-y-2 py-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center space-x-3 px-4 py-3 rounded-xl transition-all group",
                isActive 
                  ? "bg-blue-600/10 text-blue-500 border border-blue-500/20" 
                  : "text-slate-400 hover:text-white hover:bg-[#1e293b]"
              )}
            >
              <Icon size={20} className={cn(isActive ? "text-blue-500" : "group-hover:text-white")} />
              <span className="font-medium">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-[#1e293b]">
        <button
          onClick={logout}
          className="flex items-center space-x-3 px-4 py-3 w-full text-slate-400 hover:text-red-400 hover:bg-red-400/5 rounded-xl transition-all"
        >
          <LogOut size={20} />
          <span className="font-medium">Logout</span>
        </button>
      </div>
    </aside>
  );
}
