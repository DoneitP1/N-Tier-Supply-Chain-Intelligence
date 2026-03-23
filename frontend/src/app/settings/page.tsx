"use client";

import React, { useState, useEffect } from 'react';
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
  ChevronRight,
  X,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/authStore';
import { useSettingsStore } from '@/store/settingsStore';
import api from '@/lib/api';

export default function SettingsPage() {
  const user = useAuthStore((state) => state.user);
  const { theme, language, notificationsEnabled, setTheme, setLanguage, setNotifications } = useSettingsStore();

  const [activeModal, setActiveModal] = useState<string | null>(null);
  
  // System Status State
  const [systemStatus, setSystemStatus] = useState({ graph: 'loading', postgres: 'loading', llm: 'loading' });
  
  // Form States
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [updateStatus, setUpdateStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await api.get('/api/stats/system');
        setSystemStatus(res.data);
      } catch (err) {
        setSystemStatus({ graph: 'error', postgres: 'error', llm: 'error' });
      }
    };
    fetchStatus();
  }, []);

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setUpdateStatus(null);
    if (password !== confirmPassword) {
      setUpdateStatus({ type: 'error', message: "Passwords do not match." });
      return;
    }
    setLoading(true);
    try {
      await api.put('/api/auth/update', { password });
      setUpdateStatus({ type: 'success', message: "Password updated successfully!" });
      setPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setUpdateStatus({ type: 'error', message: err.response?.data?.detail || "Failed to update password." });
    } finally {
      setLoading(false);
    }
  };

  const sections = [
    {
      title: 'Personal',
      items: [
        { id: 'profile', name: 'Profile Information', icon: User, color: 'text-blue-500', description: 'Update your personal details and avatar' },
        { id: 'security', name: 'Security', icon: Shield, color: 'text-red-500', description: 'Change password and manage security' },
        { id: 'api', name: 'API Access', icon: Key, color: 'text-amber-500', description: 'Manage your personal API keys' },
      ]
    },
    {
      title: 'Application',
      items: [
        { id: 'notifications', name: 'Notifications', icon: Bell, color: 'text-purple-500', description: notificationsEnabled ? 'Enabled for system alerts' : 'Currently disabled' },
        { id: 'language', name: 'Language & Region', icon: Globe, color: 'text-emerald-500', description: language },
        { id: 'display', name: 'Display', icon: Monitor, color: 'text-slate-400', description: `Theme: ${theme}` },
      ]
    },
    {
      title: 'Infrastructure',
      items: [
        { id: 'database', name: 'Database Connectivity', icon: Database, color: 'text-blue-500', description: 'Neo4j and PostgreSQL status' },
        { id: 'llm', name: 'LLM Orchestration', icon: Cloud, color: 'text-cyan-500', description: 'Gemini 1.5 Pro, Anthropic Claude 3.5' },
      ]
    }
  ];

  const StatusDot = ({ status }: { status: string }) => {
    const color = status === 'active' ? 'bg-emerald-500' : status === 'error' ? 'bg-red-500' : 'bg-slate-500';
    const textColor = status === 'active' ? 'text-emerald-500' : status === 'error' ? 'text-red-500' : 'text-slate-500';
    return (
      <span className={`flex items-center gap-1.5 text-xs font-bold capitalize ${textColor}`}>
        <div className={`w-1.5 h-1.5 rounded-full ${color} ${status === 'active' ? 'animate-pulse' : ''}`} />
        {status}
      </span>
    );
  };

  return (
    <DashboardLayout>
      <div className="mb-8">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="text-slate-400" />
          Settings
        </h2>
        <p className="text-slate-400 text-sm mt-1">Manage your account preferences and application configuration.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 relative">
        <div className="lg:col-span-1 space-y-6">
          <div className="glass p-8 rounded-3xl text-center border border-[#1e293b]">
            <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mx-auto mb-4 flex items-center justify-center text-3xl font-bold">
              {user?.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <h3 className="text-xl font-bold">{user?.username || 'User'}</h3>
            <p className="text-slate-500 text-sm capitalize mt-1">{user?.role || 'Analyst'}</p>
            <button 
              onClick={() => setActiveModal('profile')}
              className="mt-6 w-full py-2 bg-white/5 hover:bg-white/10 rounded-xl text-sm font-medium transition-all"
            >
              Edit Profile
            </button>
          </div>

          <div className="glass p-6 rounded-3xl border border-[#1e293b]">
            <h4 className="font-bold text-sm uppercase text-slate-500 tracking-wider mb-4">System Status</h4>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Knowledge Graph</span>
                <StatusDot status={systemStatus.graph} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">PostgreSQL DB</span>
                <StatusDot status={systemStatus.postgres} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">LLM Provider</span>
                <StatusDot status={systemStatus.llm} />
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
                    onClick={() => setActiveModal(item.id)}
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

      {/* MODALS */}
      {activeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-[#0f1115] border border-[#1e293b] rounded-3xl shadow-2xl w-full max-w-md p-6 relative animate-in fade-in zoom-in-95 duration-200">
            <button 
              onClick={() => { setActiveModal(null); setUpdateStatus(null); }}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors p-2"
            >
              <X size={20} />
            </button>

            {/* Profile / Security Modal */}
            {(activeModal === 'profile' || activeModal === 'security') && (
              <div>
                <h3 className="text-xl font-bold mb-2">Security & Profile</h3>
                <p className="text-sm text-slate-400 mb-6">Change your login password securely.</p>
                
                <form onSubmit={handleUpdatePassword} className="space-y-4">
                  {updateStatus && (
                    <div className={cn("p-3 rounded-xl text-sm flex items-center gap-2", updateStatus.type === 'success' ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" : "bg-red-500/10 text-red-500 border border-red-500/20")}>
                      {updateStatus.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                      {updateStatus.message}
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">New Password</label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full bg-[#111113] border border-[#1e293b] rounded-xl px-4 py-3 focus:outline-none focus:border-blue-500 transition-all text-white"
                      required
                      minLength={6}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">Confirm Password</label>
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full bg-[#111113] border border-[#1e293b] rounded-xl px-4 py-3 focus:outline-none focus:border-blue-500 transition-all text-white"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-3 rounded-xl transition-all active:scale-[0.98] mt-4"
                  >
                    {loading ? 'Updating...' : 'Update Password'}
                  </button>
                </form>
              </div>
            )}

            {/* API Access Modal */}
            {activeModal === 'api' && (
              <div>
                <h3 className="text-xl font-bold mb-2 flex items-center gap-2"><Key className="text-amber-500" /> API Access</h3>
                <p className="text-sm text-slate-400 mb-6">Your personal API keys for programmatic access.</p>
                
                <div className="bg-[#111113] border border-[#1e293b] rounded-xl p-4 text-center">
                  <p className="text-sm font-mono text-slate-300 break-all mb-4">ntier_live_72k1a9M8nxBq4wP2LzY5d</p>
                  <button className="text-sm font-bold text-blue-500 hover:text-blue-400 transition-colors">
                    Regenerate Key
                  </button>
                </div>
                <p className="text-xs text-center text-slate-500 mt-4">Keep your API key secure. Do not share it in public repositories.</p>
              </div>
            )}

            {/* Application Settings Modals */}
            {activeModal === 'notifications' && (
              <div>
                <h3 className="text-xl font-bold mb-2 flex items-center gap-2"><Bell className="text-purple-500" /> Notifications</h3>
                <p className="text-sm text-slate-400 mb-6">Manage how you receive alerts.</p>
                <button 
                  onClick={() => setNotifications(!notificationsEnabled)}
                  className="w-full flex items-center justify-between p-4 bg-[#111113] border border-[#1e293b] rounded-xl hover:border-slate-500 transition-colors"
                >
                  <span className="font-medium">System Alerts</span>
                  <div className={cn("w-10 h-6 rounded-full transition-colors relative", notificationsEnabled ? "bg-emerald-500" : "bg-slate-700")}>
                    <div className={cn("w-4 h-4 rounded-full bg-white absolute top-1 transition-all", notificationsEnabled ? "right-1" : "left-1")} />
                  </div>
                </button>
              </div>
            )}

            {activeModal === 'display' && (
              <div>
                <h3 className="text-xl font-bold mb-2 flex items-center gap-2"><Monitor className="text-slate-400" /> Display Theme</h3>
                <div className="grid grid-cols-2 gap-4 mt-6">
                  <button 
                    onClick={() => setTheme('light')}
                    className={cn("p-4 rounded-xl border transition-all", theme === 'light' ? "border-blue-500 bg-blue-500/10 text-blue-500 font-bold" : "border-[#1e293b] text-slate-400 hover:border-slate-500")}
                  >
                    Light
                  </button>
                  <button 
                    onClick={() => setTheme('dark')}
                    className={cn("p-4 rounded-xl border transition-all", theme === 'dark' ? "border-blue-500 bg-blue-500/10 text-blue-500 font-bold" : "border-[#1e293b] text-slate-400 hover:border-slate-500")}
                  >
                    Dark
                  </button>
                </div>
              </div>
            )}

            {activeModal === 'language' && (
              <div>
                <h3 className="text-xl font-bold mb-2 flex items-center gap-2"><Globe className="text-emerald-500" /> Language</h3>
                <div className="space-y-2 mt-4">
                  {['en-US', 'tr-TR'].map(lang => (
                     <button 
                     key={lang}
                     onClick={() => setLanguage(lang)}
                     className={cn("w-full text-left p-4 rounded-xl border transition-all", language === lang ? "border-blue-500 bg-blue-500/10 text-blue-500 font-bold" : "border-[#1e293b] text-slate-400 hover:border-slate-500")}
                   >
                     {lang === 'en-US' ? 'English (US)' : 'Türkçe (TR)'}
                   </button>
                  ))}
                </div>
              </div>
            )}

            {/* Read-Only Infrastructure/Info */}
            {(activeModal === 'database' || activeModal === 'llm') && (
              <div>
                <h3 className="text-xl font-bold mb-2">Infrastructure Information</h3>
                <p className="text-sm text-slate-400 mb-6">These settings are managed at the environment level and cannot be changed from the UI.</p>
                <button 
                  onClick={() => setActiveModal(null)}
                  className="w-full py-3 bg-white/10 hover:bg-white/20 rounded-xl transition-colors font-semibold"
                >
                  Understood
                </button>
              </div>
            )}

          </div>
        </div>
      )}

    </DashboardLayout>
  );
}
