"use client";

import DashboardLayout from '@/components/layout/DashboardLayout';
import { 
  Users, 
  Package, 
  AlertTriangle, 
  TrendingUp 
} from 'lucide-react';

export default function Dashboard() {
  const stats = [
    { name: 'Total Suppliers', value: '1,248', change: '+12%', icon: Users, color: 'text-blue-500', bg: 'bg-blue-500/10' },
    { name: 'Mapped Parts', value: '45,032', change: '+5%', icon: Package, color: 'text-purple-500', bg: 'bg-purple-500/10' },
    { name: 'Active Risks', value: '18', change: '-2', icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-500/10' },
    { name: 'Supply Health', value: '94.2%', change: '+1.4%', icon: TrendingUp, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  ];

  return (
    <DashboardLayout>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="glass p-6 rounded-2xl">
              <div className="flex justify-between items-start mb-4">
                <div className={cn("p-3 rounded-xl", stat.bg)}>
                  <Icon size={24} className={stat.color} />
                </div>
                <span className={cn(
                  "text-xs font-semibold px-2 py-1 rounded-full",
                  stat.change.startsWith('+') ? "bg-emerald-500/10 text-emerald-500" : "bg-red-500/10 text-red-500"
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

// Simple export fix for helper
import { cn } from '@/lib/utils';
