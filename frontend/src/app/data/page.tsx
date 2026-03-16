"use client";

import React, { useState, useEffect } from 'react';
import { 
  Database, 
  Search, 
  Filter, 
  Download, 
  Loader2, 
  Users, 
  Package,
  MoreVertical,
  ExternalLink
} from 'lucide-react';
import DashboardLayout from '@/components/layout/DashboardLayout';
import api from '@/lib/api';
import { cn } from '@/lib/utils';

interface Entity {
  id: number;
  label: string;
  name: string;
}

export default function DataManagementPage() {
  const [activeTab, setActiveTab] = useState<'Supplier' | 'Part'>('Supplier');
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const fetchEntities = async () => {
      setLoading(true);
      try {
        const response = await api.get(`/api/graph/nodes?label=${activeTab}`);
        setEntities(response.data);
      } catch (err) {
        console.error(`Failed to fetch ${activeTab}s`, err);
      } finally {
        setLoading(false);
      }
    };
    fetchEntities();
  }, [activeTab]);

  const filteredEntities = entities.filter(e => 
    e.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <DashboardLayout>
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Database className="text-blue-500" />
            Data Management
          </h2>
          <p className="text-slate-400 text-sm mt-1">Explore and manage entities in the N-Tier Knowledge Graph.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-[#1e293b] hover:bg-[#2e3e56] rounded-xl text-sm transition-all border border-[#1e293b]">
            <Download size={16} />
            Export CSV
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="lg:col-span-1 space-y-4">
          <div className="glass p-2 rounded-2xl flex flex-col gap-1">
            <button 
              onClick={() => setActiveTab('Supplier')}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-sm font-medium",
                activeTab === 'Supplier' ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20" : "text-slate-400 hover:bg-white/5"
              )}
            >
              <Users size={18} />
              Suppliers
            </button>
            <button 
              onClick={() => setActiveTab('Part')}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-sm font-medium",
                activeTab === 'Part' ? "bg-purple-600 text-white shadow-lg shadow-purple-500/20" : "text-slate-400 hover:bg-white/5"
              )}
            >
              <Package size={18} />
              Parts Catalog
            </button>
          </div>

          <div className="glass p-6 rounded-3xl border border-[#1e293b]">
            <h4 className="font-bold mb-4 text-sm uppercase text-slate-500 tracking-wider">Filters</h4>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-slate-500 mb-2 block">Quick Search</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
                  <input 
                    type="text" 
                    placeholder="Search by name..."
                    className="w-full bg-[#0d0d0f] border border-[#1e293b] rounded-xl pl-10 pr-4 py-2 text-sm outline-none focus:border-blue-500 transition-all"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-3">
          {loading ? (
            <div className="glass rounded-3xl p-12 flex flex-col items-center justify-center text-center">
              <Loader2 className="animate-spin text-blue-500 mb-4" size={48} />
              <p className="text-slate-400">Loading catalog data...</p>
            </div>
          ) : (
            <div className="glass rounded-3xl overflow-hidden border border-[#1e293b]">
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="bg-white/5 border-b border-[#1e293b]">
                      <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Entity Name</th>
                      <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Type</th>
                      <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">System ID</th>
                      <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1e293b]">
                    {filteredEntities.map((entity) => (
                      <tr key={entity.id} className="hover:bg-white/[0.02] transition-colors group">
                        <td className="px-6 py-4">
                          <span className="font-semibold">{entity.name}</span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={cn(
                            "px-3 py-1 rounded-full text-[10px] font-bold uppercase",
                            entity.label === 'Supplier' ? "bg-blue-500/10 text-blue-500" : "bg-purple-500/10 text-purple-500"
                          )}>
                            {entity.label}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <code className="text-xs text-slate-500 font-mono">#{entity.id}</code>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                             <button className="p-2 hover:bg-white/5 rounded-lg transition-all text-slate-500 hover:text-white">
                              <ExternalLink size={16} />
                            </button>
                            <button className="p-2 hover:bg-white/5 rounded-lg transition-all text-slate-500 hover:text-white">
                              <MoreVertical size={16} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {filteredEntities.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-6 py-12 text-center text-slate-500">
                          No {activeTab.toLowerCase()}s found matching your search.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
