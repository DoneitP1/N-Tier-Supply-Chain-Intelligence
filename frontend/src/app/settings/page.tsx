"use client";

import React from 'react';
import { 
  Settings, 
  User, 
  Shield, 
  Bell, 
  Globe, 
  Key,
  Database,
  Monitor,
  Cloud,
  ChevronRight
} from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/authStore';

export default function SettingsPage() {
  const user = useAuthStore((state) => state.user);

  const sections = [
    {
      title: 'Personal',
      items: [
        { name: 'Profile Information', icon: User, color: 'text-blue-500', description: 'Update your personal details and avatar' },
        { name: 'Security', icon: Shield, color: 'text-red-500', description: 'Password, 2FA and login activity' },
        { name: 'API Access', icon: Key, color: 'text-amber-500', description: 'Manage your personal API keys' },
      ]
    },
    {
      title: 'Application',
      items: [
        { name: 'Notifications', icon: Bell, color: 'text-purple-500', description: 'Configure system alerts and risk feeds' },
        { name: 'Language & Region', icon: Globe, color: 'text-emerald-500', description: 'English (US), UTC+0' },
        { name: 'Display', icon: Monitor, color: 'text-slate-400', description: 'Dark mode, chart themes and layout' },
      ]
    },
    {
      title: 'Infrastructure',
      items: [
        { name: 'Database Connectivity', icon: Database, color: 'text-blue-500', description: 'Neo4j and PostgreSQL status' },
        { name: 'LLM Orchestration', icon: Cloud, color: 'text-cyan-500', description: 'Gemini 1.5 Pro, Anthropic Claude 3.5' },
      ]
    }
  ];

  return (
    <DashboardLayout>
      <div className="mb-8">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="text-slate-400" />
          Settings
        </h2>
        <p className="text-slate-400 text-sm mt-1">Manage your account preferences and application configuration.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1 space-y-6">
          <div className="glass p-8 rounded-3xl text-center border border-[#1e293b]">
            <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mx-auto mb-4 flex items-center justify-center text-3xl font-bold">
              {user?.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <h3 className="text-xl font-bold">{user?.username || 'User'}</h3>
            <p className="text-slate-500 text-sm capitalize mt-1">{user?.role || 'Analyst'}</p>
            <button className="mt-6 w-full py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm font-medium transition-all">
              Edit Profile
            </button>
          </div>

          <div className="glass p-6 rounded-3xl border border-[#1e293b]">
            <h4 className="font-bold text-sm uppercase text-slate-500 tracking-wider mb-4">System Status</h4>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Knowledge Graph</span>
                <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-500">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Active
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">PostgreSQL DB</span>
                <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-500">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Active
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">LLM Provider</span>
                <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-500">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  Online
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-8">
          {sections.map((section) => (
            <div key={section.title}>
              <h4 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-4 px-2">{section.title}</h4>
              <div className="glass rounded-3xl overflow-hidden border border-[#1e293b] divide-y divide-[#1e293b]">
                {section.items.map((item) => (
                  <button 
                    key={item.name}
                    className="w-full flex items-center justify-between p-6 hover:bg-white/[0.02] transition-colors text-left group"
                  >
                    <div className="flex items-center gap-4">
                      <div className={cn("p-3 rounded-2xl bg-white/5 group-hover:bg-white/10 transition-colors", item.color.replace('text', 'bg').replace('500', '500/10'))}>
                        <item.icon size={22} className={item.color} />
                      </div>
                      <div>
                        <p className="font-bold">{item.name}</p>
                        <p className="text-sm text-slate-500 mt-0.5">{item.description}</p>
                      </div>
                    </div>
                    <ChevronRight className="text-slate-700 group-hover:text-slate-400 transition-all" size={20} />
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
