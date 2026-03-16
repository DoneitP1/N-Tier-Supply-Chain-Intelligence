"use client";

import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { 
  Users, 
  Package, 
  AlertTriangle, 
  TrendingUp,
  Loader2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import api from '@/lib/api';

interface StatsData {
  total_suppliers: number;
  total_parts: number;
  active_risks: number;
  supply_health: number;
  trends: {
    suppliers: string;
    parts: string;
    risks: string;
    health: string;
  };
}

export default function Home() {
  const [statsData, setStatsData] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/stats');
        setStatsData(response.data);
        setError(null);
      } catch (err: any) {
        console.error('Failed to fetch stats:', err);
        setError('Failed to load dashboard statistics.');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  const stats = statsData ? [
    { 
      name: 'Total Suppliers', 
      value: statsData.total_suppliers.toLocaleString(), 
      change: statsData.trends.suppliers, 
      icon: Users, 
      color: 'text-blue-500', 
      bg: 'bg-blue-500/10' 
    },
    { 
      name: 'Mapped Parts', 
      value: statsData.total_parts.toLocaleString(), 
      change: statsData.trends.parts, 
      icon: Package, 
      color: 'text-purple-500', 
      bg: 'bg-purple-500/10' 
    },
    { 
      name: 'Active Risks', 
      value: statsData.active_risks.toString(), 
      change: statsData.trends.risks, 
      icon: AlertTriangle, 
      color: 'text-red-500', 
      bg: 'bg-red-500/10' 
    },
    { 
      name: 'Supply Health', 
      value: `${statsData.supply_health}%`, 
      change: statsData.trends.health, 
      icon: TrendingUp, 
      color: 'text-emerald-500', 
      bg: 'bg-emerald-500/10' 
    },
  ] : [];

  return (
    <DashboardLayout>
      {loading ? (
        <div className="flex items-center justify-center p-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <span className="ml-3 text-slate-400">Loading dashboard data...</span>
        </div>
      ) : error ? (
        <div className="p-6 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-500 mb-8">
          {error}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat) => {
            const Icon = stat.icon;
            const isNeutral = stat.change === '0' || stat.change === '+0%' || stat.change === '-0%';
            const isPositive = stat.change.startsWith('+');
            
            return (
              <div key={stat.name} className="glass p-6 rounded-2xl">
                <div className="flex justify-between items-start mb-4">
                  <div className={cn("p-3 rounded-xl", stat.bg)}>
                    <Icon size={24} className={stat.color} />
                  </div>
                  <span className={cn(
                    "text-xs font-semibold px-2 py-1 rounded-full",
                    isNeutral ? "bg-slate-500/10 text-slate-500" :
                    isPositive ? "bg-emerald-500/10 text-emerald-500" : 
                    "bg-red-500/10 text-red-500"
                  )}>
                    {stat.change}
                  </span>
                </div>
                <div>
                  <p className="text-slate-400 text-sm">{stat.name}</p>
                  <p className="text-3xl font-bold mt-1">{stat.value}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 glass p-6 rounded-2xl h-[400px]">
          <h3 className="text-lg font-semibold mb-6">Recent Supply Disruptions</h3>
          <div className="flex items-center justify-center h-full text-slate-500">
            Graph/Chart Visualization Placeholder
          </div>
        </div>
        <div className="glass p-6 rounded-2xl h-[400px]">
          <h3 className="text-lg font-semibold mb-6">Risk Feed</h3>
          <div className="space-y-4 overflow-y-auto h-[300px]">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="p-4 rounded-xl bg-[#1e293b]/30 border border-[#1e293b] flex items-start space-x-3">
                <div className="w-2 h-2 rounded-full bg-red-500 mt-2 shrink-0" />
                <div>
                  <p className="text-sm font-medium">Logistics Strike - Port of Hamburg</p>
                  <p className="text-xs text-slate-500 mt-1">2 hours ago • Severity: High</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
